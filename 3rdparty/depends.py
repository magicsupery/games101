# -*- coding: utf-8 -*-
import yaml
import sys
import os
import shutil
import platform
import atexit
import subprocess
import getopt

SOURCE_DIR = "source"
BUILD_DIR = "build"




WIN_COMPILER = "mingw"
CMAKE_BUILD_TYPE = "Debug"
MACOS_BUILD_TRAGET = "ios"

# read config file (depends.yaml)
config = None

from collections import OrderedDict

def ordered_load(stream, Loader=yaml.Loader, object_pairs_hook=OrderedDict):
    class OrderedLoader(Loader):
        pass
    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))
    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)
    return yaml.load(stream, OrderedLoader)


def get_config():
    global config
    yaml_file = "depends.yaml"
    if platform.system().lower() == "darwin":
        yaml_file += '.'+MACOS_BUILD_TRAGET
        print('YAML: ', yaml_file)
    
    with open(yaml_file) as f:
        try:
            config = ordered_load(f, yaml.SafeLoader)
        except yaml.YAMLError as e:
            print (e)

    assert config is not None
    print (config)
    return config

# log.txt
log = open("log.txt", "w", 1024)
@atexit.register
def close_log():
    log.flush()
    log.close()

class Logger(object):
    def __init__(self):
        # backup old stdout
        self.terminal = sys.stdout

    def write(self, messgae):
        try:
            self.terminal.write(messgae)
            log and log.write(messgae)
        except Exception as err:
            log and log.write(err.__str__() + messgae)

logger = Logger()
sys.stdout = logger
sys.stderr = logger

# check os
os_name = platform.system().lower()
print("os name is ", os_name)
BUILD_OS = [v for k, v in {"win": "win", "windows": "windows", "darwin": "osx", "linux" : "linux"}.items() if k == os_name][0]
print ("Build OS: ", BUILD_OS)


def create_dir(dir_name):
    if not os.path.exists(dir_name):
        os.mkdir(dir_name)

def remove_dir(dir_name):
    if os.path.exists(dir_name):
        dir_name = '\\\\?\\' + dir_name
        shutil.rmtree(dir_name)

def create_empty_dir(dir_name):
    remove_dir(dir_name)
    create_dir(dir_name)

# get real path

def get_real_path():
    global SOURCE_DIR, BUILD_DIR
    SOURCE_DIR = os.path.realpath(config.get("source", "source"))
    BUILD_DIR = os.path.realpath(config.get("build", "build"))
    print ('Source Dir: ', SOURCE_DIR)
    print ('Build Dir:', BUILD_DIR)

    create_dir(SOURCE_DIR)
    create_dir(BUILD_DIR)


def run_cmd(cmd):
    print ('-- run -- ', cmd)
    poll_code = None
    try:
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)
        while True:
            output = p.stdout.readline()
            if output:
                print (output,)
            poll_code = p.poll()
            if poll_code is not None:
                break
    except Exception as e:
        p.terminate()
        print (e)
    finally:
        # flush, counldn't block here
        p.stdout.flush()
        output =  p.stdout.read()
        if output:
            print (output,)
    assert poll_code == 0, 'run cmd failed, code %s!'%poll_code


class Builder(object):
    def __init__(self, target=None):
        self.ninja = None

    def build_ninja(self):
        source_dir = os.path.join(SOURCE_DIR, "ninja")
        build_dir = os.path.join(BUILD_DIR, "ninja")

        suffix = ".exe" if BUILD_OS == "win" else ""
        self.ninja = os.path.join(build_dir, "ninja%s"%(suffix, ))
        if os.path.exists(self.ninja):
            print ('================== Ninja Alredy Build, Skipped... ==================')
            return

        create_empty_dir(build_dir)

        if os_name == "win" or os_name == "windows":
            if WIN_COMPILER == "":
                print ('error: need point out "mingw" or "msvc" on windows')
                exit(0)
            else:
                cmd = "cd %s && python %s/configure.py --bootstrap --platform %s "%(build_dir, source_dir, WIN_COMPILER)
        else:
            cmd = "cd %s && python %s/configure.py --bootstrap "%(build_dir, source_dir)
        run_cmd(cmd)

    def clean(self):
        remove_dir(BUILD_DIR)

    def build_one_lib(self, lib_name, cmake_dir, cmake_args=None):
        source_dir = os.path.join(SOURCE_DIR, lib_name)
        if not os.path.exists(source_dir):
            source_dir = os.path.join(SOURCE_DIR, "..", lib_name)
        if not os.path.exists(source_dir):
            print ('error', lib_name, 'not exist')
            return

        build_dir = os.path.join(BUILD_DIR, lib_name)
        install_dir = os.path.realpath(config.get("install", "install"))

        create_empty_dir(build_dir)

        now_path = os.path.realpath(".")
        os.chdir(build_dir)

        print ('================== BUILD %s BEGIN =================='%(lib_name.upper(), ))
        final_cmake_args = []
        final_cmake_args.extend(config.get("cmake_args", []))

        if cmake_args:
            final_cmake_args.extend(cmake_args)
        final_cmake_args.append("-DCMAKE_BUILD_TYPE=%s"%CMAKE_BUILD_TYPE)
        final_cmake_args.append("-DCMAKE_INSTALL_PREFIX=%s"%(install_dir,))
        final_cmake_args.append("-DCMAKE_MAKE_PROGRAM=%s"%self.ninja)
        
        if WIN_COMPILER == "msvc":
            syspath = os.environ["path"].split(";")
            for i in range(len(syspath)):
                if "mingw" in syspath[i]:
                    print(syspath[i])
                    final_cmake_args.append("-DCMAKE_IGNORE_PATH=%s" %syspath[i])
                    break

        cmake_arg_str = " ".join(final_cmake_args)
        cmd = " ".join(["cmake -G Ninja", cmake_arg_str, "%s/%s"%(source_dir, cmake_dir)])

        run_cmd(cmd)
        run_cmd(self.ninja)
        try:
            run_cmd(self.ninja + " install")
        except:
            print ("no install function in ", lib_name)

        print ('================== BUILD %s END =================='%(lib_name.upper(), ))

        os.chdir(now_path)


    def build_libs(self, sp_name=None):
        for name, attr in config["depends"].items():
            if name == "ninja" or (sp_name and sp_name != name):
                continue
            self.build_one_lib(name, "", attr.get('cmake_args'))


    def download_libs(self):
        for name, attr in config["depends"].items():
            git_url = attr.get("git", None)
            if git_url:
                source_path = os.path.join(SOURCE_DIR, name)
                if not os.path.exists(source_path):
                    run_cmd("cd %s && git clone %s %s"%(SOURCE_DIR, git_url, name))
                    if attr.get('submodule'):
                        run_cmd("cd %s/%s && git submodule update --init" %(SOURCE_DIR, name))
                    if attr.get('tag'):
                        run_cmd("cd %s && git checkout %s"%(source_path, attr.get("tag")))


    def work(self):
        self.download_libs()
        self.build_ninja()
        self.build_libs()

def usage():
    print ('===========================================================================================')
    print ('======================================= Usage =============================================')
    print ('===========================================================================================')
    print ('python3 depends.py [option]')
    print ('options:')
    print ('--win=["mingw" or "msvc", default = "mingw"]')
    print ('--build=["Debug" or "Release" or "RelWithDebInfo", default = "RelWithDebInfo"]')
    print ('--macos=["andorid" or "ios" or "mac", default = "ios"')
    return

if __name__ == "__main__":
    args = 'win= build= macos='.split()
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'h', args)
    except getopt.GetoptError as err:
        print(str(err))
        usage()
        sys.exit(2)

    for opt, value in opts:
        if opt == '-h':
            usage()
            sys.exit()
        elif opt == '--win':
            if value not in ("mingw", "msvc"):
                usage()
                sys.exit(2)
            else:
                WIN_COMPILER = value
        elif opt == '--build':
            if value not in ("Debug", "Release", "RelWithDebInfo"):
                usage()
                sys.exit(2)
            else:
                CMAKE_BUILD_TYPE = value
        elif opt == '--macos':
            if value not in ("android", "ios", "mac"):
                usage()
                sys.exit(2)
            else:
                MACOS_BUILD_TRAGET = value
    print(WIN_COMPILER, CMAKE_BUILD_TYPE, MACOS_BUILD_TRAGET)
    get_config()
    get_real_path()
    Builder().work()
