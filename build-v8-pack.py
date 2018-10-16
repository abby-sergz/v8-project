#!/usr/bin/env python3
# coding: utf-8

import argparse
import errno
import logging
import os
import parser
import subprocess
import sys

this_dir_path = os.path.dirname(os.path.realpath(__file__))

def create_v8_libraries(suffix = None, sys_platform = sys.platform):
    v8_pure_libs = (["base"] if sys_platform != "win32" else ["base_" + str(i) for i in range(0, 4)]) + ["libbase", "libplatform", "libsampler", "snapshot"]
    if suffix == None:
        suffix = ".a" if sys_platform != "win32" else ".lib"
    return [("libv8_" if sys_platform != "win32" else "v8_") + lib + suffix for lib in v8_pure_libs]

v8_libraries = create_v8_libraries()

def ensure_prebuilt_dir():
    prebuilt_dir_path = os.path.join(this_dir_path, "prebuilt-v8")
    try:
        os.makedirs(prebuilt_dir_path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
    return prebuilt_dir_path

def pack_include():
    output_file_path = os.path.join(ensure_prebuilt_dir(), "include.7z")
    cmd = ["7z", "a", output_file_path, "include"]
    working_dir = os.path.join(this_dir_path, "third_party", "v8")
    subprocess.check_call(cmd, cwd = working_dir)

def pack_all_nix(dst_name_xz, lib_dir):
    output_file_path = os.path.join(ensure_prebuilt_dir(), dst_name_xz)
    cmd = ["tar", "-cJf", output_file_path] + v8_libraries
    working_dir = os.path.join(this_dir_path, *lib_dir)
    subprocess.check_call(cmd, cwd = working_dir)

def pack_nix(os_version, configuration):
    configuration_dir = configuration[:1].upper() + configuration[1:]
    pack_all_nix(os_version + "-x64-" + configuration + ".tar.xz", ["build", "v8", "out", configuration_dir])

def pack_android(target_arch):
    pack_all_nix("android-" + target_arch + "-release.tar.xz", ["build", "android_" + (target_arch if target_arch != "x86" else "ia32") + ".release"])

def pack_windows(target_arch, configuration):
    output_file_path = os.path.join(ensure_prebuilt_dir(), "win32-" + target_arch + "-" + configuration + ".7z")
    cmd = ["c:\\Program Files\\7-Zip\\7z.exe", "a", output_file_path] + create_v8_libraries()
    if configuration == "Debug":
        cmd = cmd + create_v8_libraries(".pdb")
    working_dir = os.path.join(this_dir_path, "build", target_arch, "v8", "third_party", "v8", "src", configuration)
    subprocess.check_call(cmd, cwd = working_dir)

if __name__ == '__main__':
    logging.basicConfig(format = '%(levelname)s:%(message)s', level=logging.DEBUG)
    parser = argparse.ArgumentParser(description = 'Helper to pack V8 for ABP')

    subparsers = parser.add_subparsers(title = "available subcommands", help = "additional help")

    include_arg_parser = subparsers.add_parser('pack-include')
    include_arg_parser.set_defaults(func = lambda args: pack_include())

    android_arg_parser = subparsers.add_parser('pack-android')
    android_arg_parser.add_argument('target_arch', choices = ["arm", "arm64", "x86"])
    android_arg_parser.set_defaults(func=lambda args: pack_android(args.target_arch))

    linux_arg_parser = subparsers.add_parser('pack-nix')
    linux_arg_parser.add_argument('configuration', choices = ["release", "debug"])
    linux_arg_parser.add_argument('os_version', default = "u14.04", help = "us it for 'osx'")
    linux_arg_parser.set_defaults(func = lambda args: pack_nix(args.os_version, args.configuration))

    windows_arg_parser = subparsers.add_parser('pack-windows')
    windows_arg_parser.add_argument('target_arch', choices = ["x64", "ia32"])
    windows_arg_parser.add_argument('configuration', choices = ["Release", "Debug"])
    windows_arg_parser.set_defaults(func=lambda args: pack_windows(args.target_arch, args.configuration))

    args = parser.parse_args()
    args.func(args)
