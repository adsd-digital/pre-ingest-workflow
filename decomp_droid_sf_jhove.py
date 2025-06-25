import os
import shutil
import subprocess
import traceback
from zipfile import ZipFile

import pandas as pd
import py7zr


# TODO set up log

def setup_dir():
    analyze_dir = input("Put in the path to the directory that should be analyzed.\n "
                        "If left empty, current working directory is used.\n")
    analyze_dir = analyze_dir.strip(" ").strip('"').strip("'")
    # print(analyze_dir)
    if not os.path.isdir(analyze_dir):
        # print("Not a directory")
        analyze_dir = os.getcwd()
    print(f"Analyse-Ordner ist {analyze_dir}.")
    output_dir = input("Set output directory.\n"
                       "If left empty in the directory where the analyze_dir is stored "
                       "an output folder is created.\n")
    output_dir = output_dir.strip(" ").strip('"').strip("'")
    if not os.path.isdir(output_dir):
        # print(f"{output_dir} is not a directory")
        output_dir = (analyze_dir.rstrip("/") + "_output")
        # print(f"{output_dir}")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    print(f"Output-Ordner ist {output_dir}.")
    return analyze_dir, output_dir


def droid_sf_update():
    subprocess.run(['java', '-jar',
                    '/home/dlza/Programme/droid-binary-6.8.0-bin/droid-command-line-6.8.0.jar', '-d'])
    subprocess.run(['sf', '-update'])

def droid_compressed(folderinput, droid_output):
    droidfile = os.path.join(droid_output, "droid_compressed.csv")
    subprocess.run(['java', '-jar',
                    '/home/dlza/Programme/droid-binary-6.8.0-bin/droid-command-line-6.8.0.jar',
                    folderinput, '-R', '-ff', 'file_ext any zip 7z xz rar tar gzip wim bzip2', '-f',
                    'type none FOLDER', '-o', droidfile])
    return droidfile


def droid_shutil(comp_path, fold_path):
    print(f"entpackt {comp_path}")
    try:
        shutil.unpack_archive(comp_path, fold_path)
        print("Juhu!")
    except BaseException:
        print("Fehler")
        traceback.print_exc()



# def droid_unzip(zip_path, fold_name, fold_exists):
#     print("unzip " + zip_path)
#     try:
#         with ZipFile(zip_path) as myzip:
#         #Problem an extractall: unterhalb des
#             myzip.extractall(path=fold_name)
#     except BaseException:
#         print("BAD ZIP FILE")
#         traceback.print_exc()

def droid_un7zip(sevenzip_path, fold_name):
    print("7unzip " + sevenzip_path)
    try:
        with py7zr.SevenZipFile(sevenzip_path) as my7z:
            my7z.extractall(path=fold_name)
        print("Juhu!")
    except BaseException:
        print("BAD 7z FILE")
        traceback.print_exc()


def droid_decomp_routine(droid_input):
    comp_types = {"zip": droid_shutil,
                  "tar": droid_shutil,
                  "xz": droid_shutil,
                  "7z": droid_un7zip}
    columns_needed = ['ID', 'PARENT_ID', 'URI', 'FILE_PATH', 'NAME', 'METHOD', 'STATUS', 'SIZE', 'TYPE', 'EXT',
                      'LAST_MODIFIED', 'EXTENSION_MISMATCH', 'FORMAT_COUNT', 'PUID', 'MIME_TYPE', 'FORMAT_NAME',
                      'FORMAT_VERSION']
    sth_to_unpack = False
    try:
        decomp_csv = pd.read_csv(droid_input, usecols=columns_needed)
        sth_to_unpack = True
    except pd.errors.EmptyDataError:
        print("Keine zip, 7z or gz.xz- Dateien gefunden.")
    # print(sth_to_unpack)

    if sth_to_unpack:
        for i in range(len(decomp_csv)):
            ext = decomp_csv.loc[i].EXT
            comp_file_path = decomp_csv.loc[i].FILE_PATH
            if ext in comp_types and not decomp_csv.loc[i].EXTENSION_MISMATCH:
                # print(ext)
                # print(comp_types[ext])
                folder_name = comp_file_path.rstrip("." + ext)
                # Problem: tar.xz -> wenn xz weggenommen wird, immer noch tar, dadurch:
                # schon vorhandener gleichnamiger Ordner nicht erkannt
                folder_exists = False
                if os.path.exists(folder_name):
                    folder_exists = True
                    folder_name = folder_name + "_decomp"
                    print("folder_name")
                else:
                    slash_id = folder_name.rfind("/")
                    folder_name = folder_name[:slash_id + 1]
                comp_types[ext](comp_file_path, folder_name)
            # TODO bei gleichnamigem Ordner: vergleichen
            # TODO komprimiertes Paket löschen (?)
            else:
                print(f"{ext} ist unbekanntes Kompressionsformat.\n"
                      f"Liegt an {comp_file_path}")


def droid_complete(droid_input):
    print("xx")


droid_sf_update()
analyze, output = setup_dir()
# print(analyze)
# print(output)
droid_comp = droid_compressed(analyze, output)
droid_decomp_routine(droid_comp)
