#!/usr/bin/env python3

import argparse
import json
import logging
import os
import subprocess
import sys

depot_tools_repository_url = 'https://chromium.googlesource.com/chromium/tools/depot_tools.git'
default_v8_revision = '9a7be49a7a6e435d8a7d435c4879340a3cc7524c'

this_dir_path = os.path.dirname(os.path.realpath(__file__))
third_party = 'third_party'


def read_as_json(file_path):
    with open(file_path, mode='r') as file:
        return json.load(file, encoding='UTF-8')


def sync(v8_revision):
    """Clones all required code and tools."""
    working_dir = os.path.join(this_dir_path, third_party)
    depot_tools_path = os.sep.join([working_dir, 'depot_tools'])
    # a simple way to ensure that depot_tools exists
    if not os.path.exists(depot_tools_path):
        cmd = ['git', 'clone', depot_tools_repository_url]
        subprocess.run(cmd, cwd=working_dir, check=True)
    env = os.environ.copy()
    env['PATH'] = os.pathsep.join([os.environ['PATH'], depot_tools_path])
    gclient_file = 'gclient-' + ('win' if sys.platform == 'win32' else 'nix')
    cmd_gclient_file = ['--gclientfile', gclient_file]
    call_gclient = ['gclient']
    if sys.platform == 'win32':
        env['DEPOT_TOOLS_WIN_TOOLCHAIN'] = '0'
        call_gclient[0] = call_gclient[0] + '.bat'
        call_gclient[:0] = ['cmd', '/C']
    subprocess.run(call_gclient + ['sync', '--revision', v8_revision] + cmd_gclient_file,
                   cwd=working_dir, env=env, check=True)
    subprocess.run(call_gclient + ['runhooks'] + cmd_gclient_file,
                   cwd=os.sep.join([working_dir, 'v8']), env=env, check=True)


def build_v8(target_arch, build_type, target_platform):
    """Build v8_monolith library.

    Arguments:
        target_arch - usually 'arm', 'ia32' or 'x64'
        build_type - 'release' or 'debug'
        target_platform - either 'android' or sys.platform
    """
    working_dir = os.path.join(this_dir_path, third_party, 'v8')
    output_dir = os.path.abspath(os.path.join('build', '.'.join([target_platform, target_arch, build_type])))
    call_gn = [os.path.join('..', 'depot_tools', 'gn')]
    env = os.environ.copy()
    if sys.platform == 'win32':
        env['DEPOT_TOOLS_WIN_TOOLCHAIN'] = '0'
        call_gn[0] = call_gn[0] + '.bat'
        call_gn[:0] = ['cmd', '/C']

    args_library = read_as_json('args-library.json')
    args_os = {'win32': 'windows', 'darwin': 'osx', 'linux': 'linux', 'android': 'android'}
    gn_args = args_library['common'].copy()
    for args_part in [args_os[target_platform], target_arch, build_type]:
        if args_part not in args_library:
            continue
        gn_args.update(args_library[args_part])

    def stringify(value):
        if isinstance(value, str):
            return value
        if isinstance(value, bool):
            return 'true' if value else 'false'

    args = ' '.join('{}={}'.format(kv[0], stringify(kv[1])) for kv in gn_args.items())
    cmd = call_gn + ['gen', output_dir, '--args=' + args]
    subprocess.run(cmd, cwd=working_dir, env=env, check=True)
    subprocess.run([os.sep.join([third_party, 'depot_tools', 'ninja']), '-C', output_dir, 'v8_monolith'],
                   cwd=this_dir_path, env=env, check=True)


def add_build_v8_parser(subparsers, option_name, target_platform,
                        target_arch_choices, build_type_choices):
    """Creates and returns a simple subparser."""
    parser = subparsers.add_parser(option_name)
    parser.add_argument('target_arch', choices=target_arch_choices)
    has_build_type_choice = not isinstance(build_type_choices, str)
    if has_build_type_choice:
        parser.add_argument('build_type', choices=build_type_choices)
    parser.set_defaults(func=lambda args: build_v8(args.target_arch,
                        args.build_type if has_build_type_choice else build_type_choices, target_platform))
    return parser


def print_brief_description(parser):
    """Print all available commands with all possible arguments in a comprehensive form."""
    def gen_subparsers(parser):
        for subparsers_action in parser._actions:
            if isinstance(subparsers_action, argparse._SubParsersAction):
                yield from subparsers_action.choices.values()

    # DFS
    frontier = [parser]
    while frontier:
        # pop first node from the frontier
        item = frontier.pop(0)
        # visit node
        print(item.format_usage())
        # prepend children
        frontier = list(gen_subparsers(item)) + frontier


if __name__ == '__main__':
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
    parser = argparse.ArgumentParser(description='Helper to build v8 for ABP', add_help=False)
    parser.add_argument('--help', '-h', default=False, action='store_true')
    subparsers = parser.add_subparsers(title='available subcommands', help='additional help')

    sync_arg_parser = subparsers.add_parser('sync')
    sync_arg_parser.add_argument('--revision', help='v8 revision', default=default_v8_revision)
    sync_arg_parser.set_defaults(func=lambda args: sync(args.revision))

    build_arg_parser = subparsers.add_parser('build')
    build_subparsers = build_arg_parser.add_subparsers(title='build subparsers')

    add_build_v8_parser(build_subparsers, 'windows', sys.platform, ['x64', 'ia32'], ['release', 'debug'])
    add_build_v8_parser(build_subparsers, 'nix', sys.platform, ['x64', 'ia32'], ['release', 'debug'])
    add_build_v8_parser(build_subparsers, 'android', 'android', ['arm', 'arm64', 'ia32'], 'release')

    args = parser.parse_args()
    if 'func' in args:
        args.func(args)
    elif args.help:
        parser.print_help()
    else:
        print_brief_description(parser)
