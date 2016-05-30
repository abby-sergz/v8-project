#!/usr/bin/env python3
# coding: utf-8

import argparse
import logging
import os
import re
import subprocess
import sys

default_v8_revision = '3e7dee100ac4e951719ce264f79a214f6634cf11'
this_dir_path = os.path.dirname(os.path.realpath(__file__))
third_party = 'third_party'

class Popen(subprocess.Popen):
    """This calss has check = True behaviour for subprocess.Popen as a context manager.
    """
    def __exit__(self, type, value, traceback):
        subprocess.Popen.__exit__(self, type, value, traceback)
        if self.returncode != 0:
            raise subprocess.CalledProcessError(cmd = self.args, returncode = self.returncode)

def sync(v8_revision):
    """Clones all required code and tools.
    """
    working_dir = os.path.join(this_dir_path, third_party)
    depot_tools_path = os.sep.join([working_dir, 'depot_tools'])
    # it's too simple check if someone needs more you are welcome to implement it
    if not os.path.exists(depot_tools_path):
        cmd = ['git', 'clone', 'https://chromium.googlesource.com/chromium/tools/depot_tools.git']
        subprocess.run(cmd, cwd = working_dir)
    env = {'PATH': os.pathsep.join([os.environ['PATH'], depot_tools_path])}
    if sys.platform == 'win32':
        env['DEPOT_TOOLS_WIN_TOOLCHAIN'] = 0
    cmd = ['gclient', 'sync', '--revision', v8_revision]
    with Popen(cmd, cwd = working_dir, env = env) as proc:
        pass

def build_linux(target_arch, build_type, make_params):
    """Builds v8 for using on linux

    Arguments:
        target_arch - "ia32" or "x64"
        build_type - "Release" or "Debug"
        make_params - will be added to make command, it allows to add e.g. "-j 8"
    """
    # Basically we can and should use the following command to build for linux
    # GYPFLAGS="-I../../v8-options.gypi" CXX=g++ i18nsupport=off library=shared BUILDTYPE=Release OUTDIR=../../build make x64.release -j4
    # But to be closer to the implementation for windows and for better control we manully generate
    # Makefile-based build configuration from gyp files and call make with required parameters.
    # In addition it also eliminates a couple of not used gyp defines generated by v8/Makefile.
    # To get details regarding the origin of gyp and make commands, e.g. to update current script,
    # it is recommended to check v8/Makefile and see what happens with the example command provided
    # above (add -n or add echo before actual command if -n is not enough).
    # There is also another option v8/build/gyp_v8, However it overrides some paramters and it's
    # even not used by v8/Makefile, so we don't use it either.

    working_dir = os.path.join(this_dir_path, third_party, 'v8')
    cmd = ['python', os.path.join(working_dir, 'build', 'detect_v8_host_arch.py')]
    host_arch = subprocess.run(cmd, check = True, stdout = subprocess.PIPE).stdout.decode('utf-8').strip()
    env = {'PYTHONPATH':
        os.pathsep.join([os.path.join('{V8_PATH}', 'tools', 'generate_shim_headers'),
                         os.path.join('{V8_PATH}', 'build'),
                         os.path.join('{V8_PATH}', 'build', 'gyp', 'pylib')]).format(V8_PATH = working_dir)}
    gyp_path = os.path.join(working_dir, 'build', 'gyp', 'gyp')
    # Makefiles will be stored into that directory, below it's considered to be relative to
    # working_dir
    out = os.path.sep.join(['..', '..', 'build', target_arch])
    logging.info('Generating Makefile-base build configuration into ' + os.path.join(working_dir,
        out))
    # For other parameters please refer to "gyp/gyp_main.py --help"
    cmd = [gyp_path,
        '-G make',
        '--generator-output=' + out,
        '--depth=.',
        '-I' + os.path.join('build', 'standalone.gypi'),
        '-I' + os.path.join('..', '..', 'v8-options.gypi'),
        '-Dv8_target_arch=' + target_arch, '-Dtarget_arch=' + target_arch,
        '-Dhost_arch=' + host_arch,
        os.path.join('build', 'all.gyp')]
    logging.debug(env)
    logging.debug(cmd)
    with Popen(cmd, cwd = working_dir, env = env) as proc:
        pass
    logging.info('Building {}.{}'.format(target_arch, build_type))
    # Generally speaking builddir relative to Makefile but we use absolute path because otherwise
    # make cannot find mksnapshot although the path to it and the current working directory are
    # correct.
    cmd = ['make', '-C', out, '-f', 'Makefile', 'BUILDTYPE=' +  build_type,
        'builddir=' + os.path.join(working_dir, out, build_type),
        'CC=gcc', 'CXX=g++']
    if make_params is not None:
        cmd.append(make_params)
    logging.debug(cmd)
    logging.debug(working_dir)
    with Popen(cmd, cwd = working_dir) as proc:
        pass

def build_android(target_arch, build_type, make_params):
    """
    """
    # According to the Makefile OUTDIR must be relative.
    # Paths in GYPFLAGS are relative to third_party/v8.

    # target refers to GNU make target
    target = 'android_{}.{}'.format(target_arch, build_type)
    cmd = ['make', '-C', os.path.join('third_party', 'v8'), '-f', 'Makefile.android',
           target,
           'ARCH=android_' + target_arch,
           'MODE=release',
           'OUTDIR=' + os.path.join('..', '..', 'build', target),
           'GYPFLAGS=-I' + os.path.join('..', '..', 'v8-options.gypi')]
    if make_params is not None:
        cmd.append(make_params)
    logging.info('Building {}.{}'.format(target_arch, build_type))
    logging.debug(cmd)
    logging.debug(this_dir_path)
    with Popen(cmd, cwd = this_dir_path) as proc:
        pass

def build_windows():
    """
    """
    print("Build windows")

def tests_linux(target_arch, build_type):
    """
    """
    logging.info('Testing {}.{}'.format(target_arch, build_type))
    cmd = [os.path.join('build', target_arch, build_type, 'unittests')]
    logging.debug(cmd)
    logging.debug(this_dir_path)
    with Popen(cmd, cwd = this_dir_path) as proc:
        pass

def tests_android(target_arch, build_type):
    """
    """
    logging.info('No tests for andoid so far')

if __name__ == '__main__':
    logging.basicConfig(format = '%(levelname)s:%(message)s', level=logging.DEBUG)
    parser = argparse.ArgumentParser(description = 'Helper to build v8 for ABP')
    subparsers = parser.add_subparsers(title = 'available subcommands', help = 'additional help')
    sync_arg_parser = subparsers.add_parser('sync')
    sync_arg_parser.add_argument('--revision', help = 'v8 revision', default = default_v8_revision)
    sync_arg_parser.set_defaults(func = lambda args: sync(args.revision))

    linux_arg_parser = subparsers.add_parser('build-linux')
    linux_arg_parser.add_argument('target_arch', choices = ['x64', 'ia32'])
    linux_arg_parser.add_argument('build_type', choices = ['Release', 'Debug'])
    linux_arg_parser.add_argument('--make_params',
       help = 'additional parameters for make, e.g. -j8')
    linux_arg_parser.set_defaults(func = lambda args: build_linux(args.target_arch,
        args.build_type, args.make_params))

    android_arg_parser = subparsers.add_parser('build-android')
    android_arg_parser.add_argument('target_arch', choices = ['arm', 'ia32'])
    android_arg_parser.add_argument('--make_params',
       help = 'additional parameters for make, e.g. -j8')
# add android ndk path
    android_arg_parser.set_defaults(func=lambda args: build_android(args.target_arch, 'release', args.make_params))

    windows_arg_parser = subparsers.add_parser('build-windows')
    windows_arg_parser.set_defaults(func=lambda args: build_windows())

    linux_tests_arg_parser = subparsers.add_parser('tests-linux')
    linux_tests_arg_parser.add_argument('target_arch', choices = ['x64', 'ia32'])
    linux_tests_arg_parser.add_argument('build_type', choices = ['Release', 'Debug'])
    linux_tests_arg_parser.set_defaults(func=lambda args: tests_linux(args.target_arch,
        args.build_type))
    android_tests_arg_parser = subparsers.add_parser('tests-android')
    android_tests_arg_parser.add_argument('target_arch', choices = ['arm', 'ia32'])
    android_tests_arg_parser.set_defaults(func=lambda args: tests_android(args.target_arch,
        'release'))

    args = parser.parse_args()
    args.func(args)
