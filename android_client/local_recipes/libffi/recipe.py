from pythonforandroid.recipe import Recipe
from pythonforandroid.util import current_directory
import os

class LibffiRecipe(Recipe):
    version = '3.4.4'
    url = 'https://github.com/libffi/libffi/archive/refs/tags/v{version}.tar.gz'
    
    def build_arch(self, arch):
        env = self.get_recipe_env(arch)
        # КРИТИЧНО: отключаем ошибки для устаревших макросов autoconf
        env['CFLAGS'] += ' -Wno-error=implicit-function-declaration -Wno-error=incompatible-pointer-types'
        env['WARNINGS'] = 'none'
        
        with current_directory(self.get_build_dir(arch.arch)):
            # Запускаем configure с нашими флагами
            if not os.path.isfile('configure'):
                self.sh_command('./autogen.sh', _env=env)
            self.sh_command(
                './configure ' + 
                ' '.join([
                    f'--host={arch.command_prefix}',
                    f'--prefix={self.get_build_dir(arch.arch)}',
                    '--disable-builddir',
                    '--disable-static',
                    '--with-sysroot=' + arch.ndk_sysroot,
                ]),
                _env=env
            )
            self.sh_make('install', _env=env)