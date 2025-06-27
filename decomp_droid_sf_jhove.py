import os
import shutil
import subprocess
import traceback
from zipfile import ZipFile

import numpy as np
import pandas as pd
import py7zr
from io import StringIO


# TODO set up log

def setup_dir(root, dir_name):
    dir_path = os.path.join(root, dir_name)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    return dir_path


def setup_config():
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
    update = False
    update_yn = input("Do you want to update Droid and siegfried? If yes, please type Y.\n"
                      "Otherwise update will be skipped.")
    if update_yn == "Y":
        update = True
    decomp_yn = input("Should the script try to decompress archives? Then please type Y.\n"
                      "Default is no.")
    if decomp_yn == "Y":
        decomp = True
    else:
        decomp = False
    hash_yn = input("Should droid generate hash sums? Then please type Y.\n"
                    "Default is no.")
    if hash_yn == "Y":
        hash = True
    else:
        hash = False
    ## True for Testing purposes!!
    do_jhove = True
    jhove_yn = input("Do you want to do a jhove validation?\n "
                     "If yes, please type Y.\n"
                     "Default is YES.")
    if jhove_yn == "Y":
        do_jhove = True
    mk_copies = False
    copies_yn = input("Do you want the script to generate copies for files with uncertain or incorrect formats?\n "
                      "If yes, please type Y.\n"
                      "Otherwise no copies will be made.")
    if copies_yn == "Y":
        mk_copies = True
    return analyze_dir, output_dir, update, decomp, hash, do_jhove, mk_copies


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


def droid_complete(folder_input, droid_output, hash_generation):
    complete_droid = os.path.join(droid_output, "droid_complete.droid")
    complete_droid_csv = os.path.join(droid_output, "droid_complete.csv")

    genHash = 'generateHash=false'
    if hash_generation:
        genHash = 'generateHash=true'
    # Warning: Running droid creates a derby.log file in the CWD.
    subprocess.run(['java', '-jar',
                    '/home/dlza/Programme/droid-binary-6.8.0-bin/droid-command-line-6.8.0.jar',
                    '-R', '-a', folder_input, '-At', '-Wt', '-Pr', genHash, '-p', complete_droid])
    subprocess.run(['java', '-jar',
                    '/home/dlza/Programme/droid-binary-6.8.0-bin/droid-command-line-6.8.0.jar',
                    '-p', complete_droid, '-E', complete_droid_csv])

    return complete_droid_csv


def sf_analyze(droid_file, output_folder):
    # Achtung: beim Einlesen werde manche Dateitypen geändert, z.B. Int zu Float(?)
    droid_complete_csv = pd.read_csv(droid_file)
    droid_complete_csv[['sf_id', 'sf_warning', 'sf_errors']] = None
    droid_sf_csv = os.path.join(output_folder, "droid_sf.csv")
    for i in range(len(droid_complete_csv)):
        #for i in range(5):
        #print(droid_complete_csv['NAME'].iloc[i])
        if droid_complete_csv['TYPE'].iloc[i] == ('File' or 'Container'):
            sf_an_path = droid_complete_csv['FILE_PATH'].iloc[i]
            # print(sf_an_path)
            droid_fmt = droid_complete_csv['PUID'].iloc[i]
            droid_fmt_count = droid_complete_csv['FORMAT_COUNT'].iloc[i]
            # print(type(sf_an_path))
            # print(droid_fmt)
            # print(droid_fmt_count)
            # sf_res = subprocess.run(['sf', '-csv', sf_an_path])
            #try:
            sf_res = subprocess.check_output(['sf', '-csv', sf_an_path], text=True)
            #except BaseException:
            #    print("Fehler")
            #    traceback.print_exc()
            csv_io = StringIO(sf_res)
            df_sf_res = pd.read_csv(csv_io)
            # print(df_sf_res.columns)
            # print(df_sf_res['id'].iloc[0])
            # droid_complete_csv['sf_id'].iloc[i] = df_sf_res['id'].iloc[0]
            droid_complete_csv.loc[i, 'sf_id'] = df_sf_res['id'].iloc[0]
            droid_complete_csv.loc[i, 'sf_warning'] = df_sf_res['warning'].iloc[0]
            droid_complete_csv.loc[i, 'sf_errors'] = df_sf_res['errors'].iloc[0]
    #print(droid_complete_csv['PARENT_ID'].iloc[i])
    droid_complete_csv['PARENT_ID'] = (
        pd.to_numeric(droid_complete_csv['PARENT_ID'], errors='coerce').astype('Int64'))
    droid_complete_csv['SIZE'] = (
        pd.to_numeric(droid_complete_csv['SIZE'], errors='coerce').astype('Int64'))
    droid_complete_csv['FORMAT_COUNT'] = (
        pd.to_numeric(droid_complete_csv['FORMAT_COUNT'], errors='coerce').astype('Int64'))
    droid_complete_csv.to_csv(droid_sf_csv)

    return droid_complete_csv


def jhove_and_copy(droid_sf_analysis, output_folder, dojh, mkcp):
    droid_sf_analysis[['sf_EQ_droid', 'jh_RepMod', 'jh_status', 'jh_error', 'jh_error_id']] = None
    #jhove_formats = ['fmt']
    cppath = ''
    if mkcp:
        folders = {'not_valid_dir': 'not_valid',
                   'unwell_dir': 'not_well_formed',
                   'mult_dir': 'mult_fmt_id'}
        for f in folders:
            fold_path = setup_dir(output_folder, folders[f])
            folders[f] = fold_path
    for i in range(len(droid_sf_analysis)):
        # Bedingungen noch verfeinern
        if droid_sf_analysis.loc[i, 'TYPE'] == ('File' or 'Container'):
            file_path = droid_sf_analysis.loc[i, 'FILE_PATH']
            if droid_sf_analysis['sf_id'].iloc[i] != droid_sf_analysis['PUID'].iloc[i]:
                droid_sf_analysis.loc[i, 'sf_EQ_droid'] = False
                #dest_file = os.path.join(folders['mult_dir'], os.path.basename(file_path))
                cppath = folders['mult_dir']
            else:
                droid_sf_analysis.loc[i, 'sf_EQ_droid'] = True
                # Prüfen: gibt es Fälle, wenn !=1 und trotzdem korrekt erkannt?
                # Sinnvoller: jhove auswählen lassen oder HUL festlegen?
                # oder Liste von Formaten, um Bytestream-"Prüfung" auszuschließen?
                if droid_sf_analysis.loc[i, 'FORMAT_COUNT'] == 1:
                    jhove_output = subprocess.check_output(['jhove', file_path], text=True)
                    jhove_output_array = jhove_output.split('\n')
                    for item in jhove_output_array:
                        bytestream = False
                        error_fd = False
                        if "ReportingModule: " in item:
                            mod = item.split(': ')[1].split(',')[0]
                            droid_sf_analysis.loc[i, 'jh_RepMod'] = mod
                            if mod == 'BYTESTREAM':
                                bytestream = True
                        if "Status: " in item:
                            status = item.split(': ')[1]
                            if status == 'Not well-Formed':
                                cppath = folders['unwell_dir']
                            elif status == 'Well-Formed, but not valid':
                                cppath = folders['not_valid_dir']
                            if bytestream:
                                status = "BS! " + status
                            droid_sf_analysis.loc[i, 'jh_status'] = status
                        if "ErrorMessage: " in item:
                            error_fd = True
                            error = item.split(': ')[1]
                            droid_sf_analysis.loc[i, 'jh_error'] = mod
                        if "ID: " in item:
                            if error_fd:
                                error_id = item.split(': ')[1]
                                droid_sf_analysis.loc[i, 'jh_error_id'] = error_id
                        #print(cppath)
            if mkcp and cppath != '':
                if not os.path.exists(cppath):
                    shutil.copy(file_path, cppath)

    dr_sf_jh_csv = os.path.join(output_folder, "droid_sf_jhove.csv")
    droid_sf_analysis.to_csv(dr_sf_jh_csv)
    #print(jhove_output[rpm_id:])
    # print(droid_sf_analysis['FILE_PATH'].iloc[i])


analyze, output, dsf_update, decompress, hash_gen, do_jhove, make_copy = setup_config()
# print(analyze)
# print(output)
if dsf_update:
    droid_sf_update()
if decompress:
    droid_comp = droid_compressed(analyze, output)
    droid_decomp_routine(droid_comp)
complete_droidfile = droid_complete(analyze, output, hash_gen)
# print(complete_droidfile)
droid_sf = sf_analyze(complete_droidfile, output)
jhove_and_copy(droid_sf, output, do_jhove, make_copy)
