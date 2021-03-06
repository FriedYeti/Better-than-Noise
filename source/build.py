#!/usr/bin/env python
"""Build script for Better than Noise, the Better than Wolves texture pack created by FriedYeti.

Uses Aseprite to batch export all textures to the proper structure for a Minecraft 1.5.2 texture pack.
"""

__author__ = "Carl Baumann"
__copyright__ = "Copyright 2018"

__license__ = "MIT"

import argparse
import os.path
import platform
import json
import subprocess
import shutil
import getpass

min_png_file_size = 75  # minimum file size of 16x16 png file in bytes
min_ase_file_size = 5000  # minimum file size of ase source files in bytes
max_png_00_percent = 20  # maximum percent of 00 allowed in png data, any more is an empty image


def guess_aseprite_install():
    sys = platform.system()

    if sys is '':
        print("Unable to determine OS, please specify Aseprite's install location with the -ase flag")
        exit()

    elif sys is 'Windows':
        print('Windows OS found, checking for Aseprite install...')

        # Check for default install location
        if os.path.isfile('C:\Program Files\Aseprite\Aseprite.exe'):
            print('Aseprite found at "C:\Program Files\Aseprite\Aseprite.exe".')
            return 'C:\Program Files\Aseprite\Aseprite.exe'

        # check for default Steam install location
        elif os.path.isfile('C:\Program Files (x86)\Steam\steamapps\common\Aseprite\Aseprite.exe'):
            print('Aseprite found at "C:\Program Files (x86)\Steam\steamapps\common\Aseprite\Aseprite.exe"')
            return 'C:\Program Files (x86)\Steam\steamapps\common\Aseprite\Aseprite.exe'

        else:
            print('Cannot find install, please specify with the -ase flag')
            exit()

    elif sys is 'MacOS':
        print('MacOS found, checking for Aseprite install...')
        steam_install_pre = '/Volumes/macOS/Users/'
        steam_install_post = '/Library/Application\ Support/Steam/steamapps/common/Aseprite/Aseprite.app/Contents/MacOS/aseprite'
        steam_install = steam_install_pre + getpass.getuser() + steam_install_post

        if os.path.isfile('/Applications/Aseprite.app/Contents/MacOS/run.sh'):
            print('Aseprite found at "/Applications/Aseprite.app/Contents/MacOS/run.sh"')
            return '/Applications/Aseprite.app/Contents/MacOS/run.sh'

        elif os.path.isfile(steam_install):
            print('Aseprite found at "' + steam_install + '"')
            return steam_install
        else:
            print('Cannot find install, please specify with the -ase flag')
            exit()


def aseprite_cli_export(ase_location, ase_file, folder):
    subprocess.run([ase_location, '-b', ase_file, '--save-as', folder + '/{slice}.png'])


def remove_empty_images(scan_dir, verbose):
    # TODO verify png file size works on macos and linux

    for file in os.listdir(scan_dir):
        filename = os.fsdecode(file)
        # if filename.endswith(".png") and os.path.getsize(scan_dir + '/' + file) <= min_png_file_size:
        if filename.endswith(".png") and check_if_png_empty(scan_dir+'/'+filename, verbose):
            if verbose is True:
                print(file + " is an empty image. Deleting...")
            os.remove(scan_dir + '/' + file)


def check_if_png_empty(image, verbose):
    with open(image, 'rb') as infile:
        file_data = infile.read()
        hex_string = file_data.hex()

        IDAT_sep_string = hex_string.split('49444154')
        if len(IDAT_sep_string) > 1:
            png_header = IDAT_sep_string[0]
            IDAT_chunk = IDAT_sep_string[1]

            # IDAT length is stored in the last 4 bytes before the chunk type
            IDAT_length_hex = png_header[-8:]
            IDAT_length = int(IDAT_length_hex, 16)

            # image data is stored after IDAT (4 bytes) and 2 more bytes until last 4 bytes, and is followed by 12 bytes for IEND
            image_data = IDAT_chunk[12:-32]
            if verbose:
                print(image + " has " + str(image_data.count('00')) + "/" + str(IDAT_length) + " = " + str(
                    (image_data.count('00')) / IDAT_length * 100) + " % '00's in PNG data.")
            return ((image_data.count('00')) / IDAT_length * 100) > max_png_00_percent


def build_texture_pack():
    # Set up Command line argument detection
    parser = argparse.ArgumentParser(
        description="Use Aseprite to export all textures to Minecraft's texture pack folder structure")
    parser.add_argument('-l', '--location', help='where to build the texture pack to, defaults to same directory')
    parser.add_argument('-bf', '--build_folder', action='store_true',
                        help='build to a new BUILD folder of the selected directory')
    parser.add_argument('-z', '--zip', action='store_true', help='zip final build folder')
    parser.add_argument('-v', '--verbose', action='store_true', help='enable verbose output')
    parser.add_argument('-ase', '--aseprite', help='install location of Aseprite')

    args = parser.parse_args()

    if args.location is None:
        build_directory = os.getcwd()
    else:
        if not os.path.exists(args.location):
            os.makedirs(args.location)
        build_directory = args.location

    if args.build_folder is True:
        build_directory += '/BUILD'

    if args.aseprite is None:
        aseprite_location = guess_aseprite_install()
    else:
        aseprite_location = args.aseprite

    print(build_directory)
    print(aseprite_location)

    with open('file_structure.json', 'r') as file_struct:
        j_struct = json.load(file_struct)

        # Create build directory and folder structure
        for j, value in j_struct.items():
            if value['filetype'] == 'dir':
                if not os.path.exists(build_directory + '/' + j):
                    if args.verbose is True:
                        print('Making directory :' + build_directory + '/' + j)
                    os.makedirs(build_directory + '/' + j)

        # Export all Aseprite files using Aseprite's CLI
        for j, value in j_struct.items():
            if value['aseprite_file'] is not '':
                if os.path.exists(value['aseprite_file']):

                    # check if aseprite files are large enough to have significant texture info (excluding pack icon)
                    if os.path.getsize(value['aseprite_file']) < min_ase_file_size and value[
                        'aseprite_file'] != "pack.aseprite":
                        if args.verbose is True:
                            print(value['aseprite_file'] + ' is an empty file, skipping export.')
                        continue

                    if args.verbose is True:
                        print('Exporting ' + value['aseprite_file'] + ' to ' + build_directory + '/' + j)
                    if value['filetype'] == 'dir':
                        aseprite_cli_export(aseprite_location, os.getcwd() + '/' + value['aseprite_file'],
                                            build_directory + '/' + j)
                    else:
                        aseprite_cli_export(aseprite_location, os.getcwd() + '/' + value['aseprite_file'],
                                            build_directory)
                else:
                    print('Unable to find ' + value['aseprite_file'] + ', skipping export.')

            # Remove any empty images, minecraft will replace missing textures with default, but empty images won't work
            if value['filetype'] == 'dir':
                remove_empty_images(build_directory + '/' + j, args.verbose)

        if args.zip is True:
            shutil.make_archive(build_directory + '_Better_than_Noise', 'zip', build_directory)


if __name__ == "__main__":
    build_texture_pack()
