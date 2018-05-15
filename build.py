#!/usr/bin/env python3
# coding: utf-8

import argparse
import errno
import logging
import os
import re
import urllib.request
import shutil
import subprocess
import stat
import sys
import time

default_v8_revision = "4fc9a2fe7f8a7ef1e7966185b39b3b541792669a"
android_ndk_URL = "http://dl.google.com/android/ndk/android-ndk-r10d-linux-x86_64.bin"

this_dir_path = os.path.dirname(os.path.realpath(__file__))
third_party = "third_party"

def read_file_lines(file_path):
    """Returns stripped lines of file at file_path.
    """
    content = []
    with open(file_path) as f:
        content = f.read().splitlines()
    return content

def sync(v8_revision):
    """Clones all required code and tools.
    """
    working_dir = os.path.join(this_dir_path, third_party)
    depot_tools_path = os.sep.join([working_dir, "depot_tools"])
    # it"s too simple check if someone needs more you are welcome to implement it
    if not os.path.exists(depot_tools_path):
        cmd = ["git", "clone", "https://chromium.googlesource.com/chromium/tools/depot_tools.git"]
        subprocess.run(cmd, cwd = working_dir, check = True)
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join([os.environ["PATH"], depot_tools_path])
    gclient_file = "gclient-" + ("win" if sys.platform == "win32" else "nix")
    cmd_gclient_file = ["--gclientfile", gclient_file]
    call_gclient = ["gclient"]
    if sys.platform == "win32":
        env["DEPOT_TOOLS_WIN_TOOLCHAIN"] = "0"
        call_gclient[0] = call_gclient[0] + ".bat"
        call_gclient[:0] = ["cmd", "/C"]
    subprocess.run(call_gclient + ["sync", "--revision", v8_revision] + cmd_gclient_file, cwd = working_dir, env = env, check = True)
    subprocess.run(call_gclient + ["runhooks"] + cmd_gclient_file, cwd = working_dir + os.sep + "v8", env = env, check = True)

def download_file(url, dest_file_path):
    downloading_started_at = time.time()
    show_interval = 5 # seconds
    last_shown_interval = 0
    def report_download_progress(chunk_number, chunk_size, total_size):
        nonlocal last_shown_interval
        current_interval = (time.time() - downloading_started_at) // show_interval
        if current_interval <= last_shown_interval:
            return
        last_shown_interval = current_interval
        if total_size > 0:
             logging.info("Download progress: {:>3d}%".format(100 * chunk_number * chunk_size // total_size))
    urllib.request.urlretrieve(url, dest_file_path, report_download_progress)

def install_git_lfs():
    """
    """
    url = "https://github.com/github/git-lfs/releases/download/v1.2.1/git-lfs-linux-amd64-1.2.1.tar.gz"
    tmp_dir_path = "/tmp"
    user_bin_path = os.path.join(os.path.expanduser("~"), "bin")
    if not os.path.exists(user_bin_path):
        os.makedirs(user_bin_path)
    if sys.platform == "win32":
        url = "https://github.com/github/git-lfs/releases/download/v1.2.1/git-lfs-windows-amd64-1.2.1.zip"
        tmp_dir_path = os.environ["TEMP"]
    dest_file_path = os.path.join(tmp_dir_path, os.path.basename(url))
    logging.info("{}\n{}".format(url, dest_file_path))
    download_file(url, dest_file_path)

    env = os.environ.copy()
    if sys.platform == "win32":
        git_lfs_exe = "git-lfs.exe"
        path_to_7zip = os.path.join(env["PROGRAMFILES"], "7-Zip", "7z.exe")
        cmd = [path_to_7zip, "e", dest_file_path, "git-lfs-windows-amd64-1.2.1\\" + git_lfs_exe, "-o{}".format(user_bin_path), "-y"]
        subprocess.run(cmd, check = True)
        subprocess.run([os.path.join(user_bin_path, git_lfs_exe), "install"], check = True)
    else:
        cmd = ["tar", "xzf", dest_file_path, "-C", user_bin_path, "--strip-components", "1", "git-lfs-1.2.1/git-lfs", "git-lfs-1.2.1/install.sh"]
        subprocess.run(cmd, check = True)
        env["PREFIX"] = user_bin_path
        install_sh = os.path.join(user_bin_path, "install.sh")
        subprocess.run([install_sh], env = env, check = True, shell = True)
        os.remove(install_sh)

def prepare_git_credentials():
    """Creates ~/.git-credentials, more info on https://git-scm.com/docs/git-credential-store.
    """
    deployment_token = "DEPLOYMENT_PERSONAL_ACCESS_TOKEN"
    if not deployment_token in os.environ:
      logging.warn("Personal access token is required to be in environment variable")
      raise Exception("Cannot prepare git credentials", "Access token is not provided")
    cmd = ["git", "config", "--global", "credential.helper", "store"]
    subprocess.run(cmd, cwd = this_dir_path, check = True)

    git_credentials_path = os.path.join(os.path.expanduser("~"), ".git-credentials")
    if os.path.exists(git_credentials_path):
        logging.warn("Git credentials will be overwritten, " + git_credentials_path)
    # Use has been informed, don"t care about deleted content here
    with open(git_credentials_path, "w") as f:
        f.write("https://{}:x-oauth-basic@github.com".format(os.environ[deployment_token]))

def prepare_git_user(repo_dir):
    """Sets user name and user e-mail."""
    cmd = ["git", "config", "user.name", "Sir build server"]
    subprocess.run(cmd, cwd = repo_dir, check = True)
    cmd = ["git", "config", "user.email", "support@adblockplus.org"]
    subprocess.run(cmd, cwd = repo_dir, check = True)

def update_repo(branch):
    """Clones or updates v8-binaries-repo. Update includes cleaning the current state.
    """
    repo_path = os.path.join(this_dir_path, third_party, "v8-binaries")
    if not os.path.exists(repo_path):
        github_user = "xxxz"
        cmd = ["git", "clone", "-b", branch, "https://github.com/{}/v8-binaries.git".format(github_user)]
        subprocess.run(cmd, cwd = os.path.join(this_dir_path, third_party), check = True)
    else:
        cmd = ["git", "fetch", "--prune", "origin"]
        subprocess.run(cmd, cwd = repo_path, check = True)
        cmd = ["git", "reset", "--hard", "origin/" + branch]
        subprocess.run(cmd, cwd = repo_path, check = True)
    return repo_path



class Deploy:
    """The class which provides interface to deploy the artifacts.
    """
    def __init__(self, os, target_arch, build_type, branch = "dev"):
        prepare_git_credentials()
        self.os = os
        self.target_arch = target_arch
        self.build_type = build_type
        self.branch = branch
        self.repo_path = update_repo(self.branch)
        prepare_git_user(self.repo_path)

    def clean_deployment(self):
        self.dest_path = os.path.join(self.repo_path, self.os + "_" + self.target_arch, self.build_type)
        logging.info("Removing " + self.dest_path)
        subprocess.run(["git", "rm", "-rf", "--ignore-unmatch", self.dest_path], cwd = self.repo_path, check = True)

    def clean_directory(self, dir_path):
        """dir_path should be relative to repo_path."""
        path = os.path.join(self.repo_path, "include")
        logging.info("Removing " + path)
        cmd = ["git", "rm", "-rf", "--ignore-unmatch", dir_path]
        subprocess.run(cmd, cwd = self.repo_path, check = True)
        if os.path.exists(path):
            shutil.rmtree(path)

    def add_file(self, src_file_path, dest_file_path):
        """dest_file_path should be relative
        """
        full_dest_file_path = os.path.join(self.dest_path, dest_file_path)
        dest_dir_path = os.path.dirname(full_dest_file_path)
        os.makedirs(dest_dir_path, exist_ok = True)
        logging.info("Adding \"{}\" to \"{}\"".format(dest_file_path, full_dest_file_path))
        shutil.copy2(src_file_path, full_dest_file_path)

    def add_file_content(self, content, dest_file_path):
        full_dest_file_path = os.path.join(self.dest_path, dest_file_path)
        dest_dir_path = os.path.dirname(full_dest_file_path)
        os.makedirs(dest_dir_path, exist_ok = True)
        logging.info("Adding content file to \"{}\"".format(dest_file_path, full_dest_file_path))
        with open(full_dest_file_path, "w") as f:
            f.write(content)

    def add_folder(self, src_folder_path, dest_path):
        """dst_path should be relative to repo_path
        """
        full_dest_folder_path = os.path.join(self.repo_path, dest_path)
        shutil.copytree(src_folder_path, full_dest_folder_path)
        cmd = ["git", "add", os.path.join(self.repo_path, dest_path)]
        subprocess.run(cmd, cwd = self.repo_path, check = True)

    def commit_and_push(self, commit):
        """
        """
        self.commit = commit
        content = "Commit: " + self.commit
        self.add_file_content(content, "info")
        cmd = ["git", "add", self.dest_path]
        subprocess.run(cmd, cwd = self.repo_path, check = True)
        cmd = ["git", "commit", "-m", "Build result for git:" + self.commit]
        subprocess.run(cmd, cwd = self.repo_path, check = True)
        cmd = ["git", "push", "origin", self.branch]
        subprocess.run(cmd, cwd = self.repo_path, check = True)

def get_current_commit(repo_path):
    """
    """
    cmd = ["git", "rev-parse", "--verify", "HEAD"]
    return subprocess.run(cmd, check = True, stdout = subprocess.PIPE).stdout.decode("utf-8").strip()

def get_v8_static_libraries(path):
    """Returns v8 static libraries at path without going deeper.
    """
    suffix = ".a" # static lib extension
    if sys.platform == "win32":
        suffix = ".lib"
    libv8_prefix = "libv8_"
    if sys.platform == "win32":
        libv8_prefix = "v8_"
    for dir_name, subdir_list, file_list in os.walk(path, True):
        if dir_name != path:
            continue
        for file_name in file_list:
            if file_name.startswith(libv8_prefix) and file_name.endswith(suffix):
                yield file_name

def deploy_nix(deploy):
    """Deploys linux or android artifacts.
    """
    deploy.clean_deployment()
    lib_dir = None
    if deploy.os == "linux":
        lib_dir = os.path.join(this_dir_path, "build", deploy.target_arch, deploy.build_type)
        deploy.clean_directory("include")
        src_include = os.path.join(this_dir_path, third_party, "v8", "include")
        deploy.add_folder(src_include, "include")
    elif deploy.os == "android":
        folder_name = "android_{}.{}".format(deploy.target_arch, deploy.build_type)
        lib_dir = os.path.join(this_dir_path, "build", folder_name, folder_name)
    for file_name in get_v8_static_libraries(lib_dir):
        full_file_path = os.path.join(lib_dir, file_name)
        deploy.add_file(full_file_path, file_name)
    shared_relative_file_path = os.path.join("lib.target", "libv8.so")
    deploy.add_file(os.path.join(lib_dir, shared_relative_file_path), shared_relative_file_path)
    commit = get_current_commit(this_dir_path)
    deploy.commit_and_push(commit)

def build_v8(target_arch, build_type, target_os = sys.platform):
    """Build v8 library on windows.

    Arguments:
        target_arch - "ia32" or "x64"
        build_type - "release" or "debug"
    """
    working_dir = os.path.join(this_dir_path, third_party, "v8")
    output_dir = os.path.abspath(os.path.join("build", target_arch, build_type))
    call_gn = [os.path.join("..", "depot_tools", "gn")]
    env = os.environ.copy()
    if sys.platform == "win32":
        env["DEPOT_TOOLS_WIN_TOOLCHAIN"] = "0"
        call_gn[0] = call_gn[0] + ".bat"
        call_gn[:0] = ["cmd", "/C"]
    args_os = {"win32": "win", "darwin": "osx", "linux": "linux", "android": "android"}
    args = read_file_lines("-".join(["args", args_os[target_os], target_arch, build_type]))
    args = [re.sub("[\s]", "", arg) for arg in args]
    args = " ".join(args).strip()
    cmd = call_gn + ["gen", output_dir, "--args=" + args]
    subprocess.run(cmd, cwd = working_dir, env = env, check = True)
    subprocess.run([os.sep.join([third_party, "depot_tools", "ninja"]), "-C", output_dir, "v8_monolith"], cwd = this_dir_path, env = env, check = True)
    
def deploy_win32(deploy):
    """Deploys windows artifacts.
    """
    deploy.clean_deployment()
    lib_dir = lib_dir = os.path.join(this_dir_path, "build", deploy.target_arch, "build", deploy.build_type)
    for file_name in get_v8_static_libraries(lib_dir):
        full_file_path = os.path.join(lib_dir, file_name)
        deploy.add_file(full_file_path, file_name)
    commit = get_current_commit(this_dir_path)
    deploy.commit_and_push(commit)

def tests_linux(target_arch, build_type):
    """Run tests on linux.

    Arguments:
        target_arch - "ia32" or "x64"
        build_type - "Release" or "Debug"
    """
    logging.info("Testing {}.{}".format(target_arch, build_type))
    cmd = [os.path.join("build", target_arch, build_type, "unittests")]
    logging.debug(cmd)
    logging.debug(this_dir_path)
    subprocess.run(cmd, cwd = this_dir_path, check = True)

def tests_android(target_arch, build_type):
    """
    """
    logging.info("No tests for andoid so far")

def add_simple_parser(subparsers, option_name, target_arch_choices, build_type_choices, defaults = None):
    """Creates a returns a simple subparser.
    """
    parser = subparsers.add_parser(option_name)
    parser.add_argument("target_arch", choices = target_arch_choices)
    parser.add_argument("build_type", choices = build_type_choices)
    if defaults is not None:
        parser.set_defaults(func=lambda args: defaults(args.target_arch, args.build_type))
    return parser

def make_linux_parsers(subparsers):
    """
    """
    target_arch_choices = ["x64", "ia32"]
    build_type_choices = ["release", "debug"]

    add_simple_parser(subparsers, "build-linux", target_arch_choices, build_type_choices, build_v8)

    add_simple_parser(subparsers, "tests-linux", target_arch_choices, build_type_choices, tests_linux)
    parser = add_simple_parser(subparsers, "deploy-linux", target_arch_choices, build_type_choices)
    parser.set_defaults(func=lambda args: deploy_nix(Deploy(os = "linux",
        target_arch = args.target_arch, build_type = args.build_type)))

def make_windows_parsers(subparsers):
    """
    """
    target_arch_choices = ["x64", "ia32"]
    build_type_choices = ["release", "debug"]

    add_simple_parser(subparsers, "build-windows", target_arch_choices, build_type_choices, build_v8)
    parser = add_simple_parser(subparsers, "deploy-windows", target_arch_choices, build_type_choices)
    parser.set_defaults(func=lambda args: deploy_win32(Deploy(os = "win32",
        target_arch = args.target_arch, build_type = args.build_type)))

def make_android_parsers(subparsers):
    """
    """
    parser = subparsers.add_parser("get-android-ndk")
    parser.set_defaults(func = lambda args: get_android_ndk())

    parser = subparsers.add_parser("build-android")
    parser.add_argument("target_arch", choices = ["arm", "arm64", "ia32"])
    parser.set_defaults(func=lambda args: build_v8(args.target_arch, "release", "android"))

    parser = subparsers.add_parser("tests-android")
    parser.add_argument("target_arch", choices = ["arm", "ia32"])
    parser.set_defaults(func=lambda args: tests_android(args.target_arch, "release"))

    parser = subparsers.add_parser("deploy-android")
    parser.add_argument("target_arch", choices = ["arm", "ia32"])
    parser.set_defaults(func=lambda args: deploy_nix(Deploy(os = "android",
        target_arch = args.target_arch, build_type = "release")))

if __name__ == "__main__":
    logging.basicConfig(format = "%(levelname)s:%(message)s", level=logging.DEBUG)
    parser = argparse.ArgumentParser(description = "Helper to build v8 for ABP")
    subparsers = parser.add_subparsers(title = "available subcommands", help = "additional help")

    sync_arg_parser = subparsers.add_parser("sync")
    sync_arg_parser.add_argument("--revision", help = "v8 revision", default = default_v8_revision)
    sync_arg_parser.set_defaults(func = lambda args: sync(args.revision))

    # Strictly speaking the platform functions should be in separate modules and the modules should be
    # also conditionally imported because it can happen that there can be some dependencies for platform
    # modules which are not avaliable on all platforms, like module to work with windows registry.
    if sys.platform == "win32":
        make_windows_parsers(subparsers)
    else:
        make_linux_parsers(subparsers)
        make_android_parsers(subparsers)

    subparser = subparsers.add_parser("install-git-lfs")
    subparser.set_defaults(func = lambda args: install_git_lfs())

    args = parser.parse_args()
    if "func" in args:
        args.func(args)
    else:
        parser.print_help()
