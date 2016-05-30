{
  'variables': {
    'component%': 'shared_library',
    'visibility%': 'hidden',
    'want_separate_host_toolset%': 1,
    'v8_enable_backtrace': 1,
    'v8_enable_i18n_support': 0,
    'v8_optimized_debug': 0,
    'v8_use_external_startup_data': 0,
    'v8_random_seed%': 0,
  },

  'conditions': [
    ['OS=="linux" or OS=="freebsd" or OS=="openbsd" or OS=="solaris" \
       or OS=="netbsd" or OS=="android"', {
      'target_defaults': {
        'cflags': [ '-pthread', '-fno-rtti', '-std=c++11', '-fexceptions', ],
        'cflags!': [ '-Werror', ],
        'ldflags': [ '-pthread', ],
      },
    }],
    ['OS=="mac"', {
      'xcode_settings': {
        'CLANG_CXX_LANGUAGE_STANDARD': 'c++11',
        'CLANG_CXX_LIBRARY': 'libc++',
        'OTHER_CPLUSPLUSFLAGS' : ['-std=c++11', '-stdlib=libc++'],
      },
    }],
  ],
  'target_conditions': [
    ['OS=="android" and not "host" in toolsets', {
      'target_defaults': {
        'cflags!': [
          '-pthread',  # Not supported by Android toolchain.
        ],
        'ldflags!': [
          '-llog'
          '-pthread',  # Not supported by Android toolchain.
        ],
      },
    }],
  ],

  'target_conditions': [[
    'OS==android and _type=="shared_library"', {
      'ldflags': ['-lstlport_static']
    }
  ]],


  'target_defaults': {
    'msvs_cygwin_shell': 0,
    'target_conditions': [
      ['_type=="static_library"', {
        'standalone_static_library': 1
      }]
    ]
  }
}
