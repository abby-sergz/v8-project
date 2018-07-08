#!/usr/bin/env python3

import argparse
import json
import logging
import os
import subprocess
import sys

default_v8_revision = 'f3a4da42f2da435d9bdb4da9c6ff4302ba129408'

this_dir_path = os.path.dirname(os.path.realpath(__file__))
third_party = 'third_party'


def read_as_json(file_path):
    with open(file_path, mode='r') as file:
        return json.load(file, encoding='UTF-8')


def sync(v8_revision):
    '''Clones all required code and tools.
    '''
    working_dir = os.path.join(this_dir_path, third_party)
    depot_tools_path = os.sep.join([working_dir, 'depot_tools'])
    # a simple way to ensure that depot_tools exists
    if not os.path.exists(depot_tools_path):
        cmd = ['git', 'clone', 'https://chromium.googlesource.com/chromium/tools/depot_tools.git']
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
    '''Build v8 library on windows.

    Arguments:
        target_arch - 'ia32' or 'x64'
        build_type - 'release' or 'debug'
    '''
    working_dir = os.path.join(this_dir_path, third_party, 'v8')
    output_dir = os.path.abspath(os.path.join('build', target_arch, build_type))
    call_gn = [os.path.join('..', 'depot_tools', 'gn')]
    env = os.environ.copy()
    if sys.platform == 'win32':
        env['DEPOT_TOOLS_WIN_TOOLCHAIN'] = '0'
        call_gn[0] = call_gn[0] + '.bat'
        call_gn[:0] = ['cmd', '/C']

    args_library = read_as_json('args-library.json')
    args_os = {'win32': 'win', 'darwin': 'osx', 'linux': 'linux', 'android': 'android'}
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
    '''Creates and returns a simple subparser.
    '''
    parser = subparsers.add_parser(option_name)
    parser.add_argument('target_arch', choices=target_arch_choices)
    has_build_type_choice = not isinstance(build_type_choices, str)
    if has_build_type_choice:
        parser.add_argument('build_type', choices=build_type_choices)
    parser.set_defaults(func=lambda args: build_v8(args.target_arch,
                        args.build_type if has_build_type_choice else build_type_choices, target_platform))
    return parser


was_help_called = False


class FullHelpAction(argparse._HelpAction):
    def __call__(self, parser, namespace, values, option_string=None):
        global was_help_called
        was_help_called = True

        def gen_subparsers(choice_item):
            choice, parser = choice_item
            for subparsers_action in parser._actions:
                if isinstance(subparsers_action, argparse._SubParsersAction):
                    yield from subparsers_action.choices.items()

        def print_choice_item(choice_item):
            choice, parser = choice_item
            print(parser.format_usage())

        # DFS
        frontier = [('', parser)]
        while frontier:
            # pop first node from the frontier
            choice_item = frontier.pop(0)
            # visit node
            print_choice_item(choice_item)
            # prepend children
            frontier = list(gen_subparsers(choice_item)) + frontier


if __name__ == '__main__':
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
    parser = argparse.ArgumentParser(description='Helper to build v8 for ABP', add_help=False)
    parser.add_argument('--help', action=FullHelpAction)
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
    elif not was_help_called:
        parser.print_help()
