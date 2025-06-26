# Script to Analyse DROID reports
# parts of the code are taken from and/or inspired by Freud (https://github.com/digital-preservation/freud 
# (Copyright (c) 2019, The National Archives)
# Inputs for this script are 
# (a) a droid report in csv (file path given when starting the program
# (b) a file format list (format-list.csv) that is located in the folder that the script is run from
# The format list needs the following columns:
# unchanged, automatic migration, manual migration, cannot be opened, delete, password protected, compressed, research started,
# not categorized yet,appraisal hint.

# This script will analyse the DROID report and categorizes the formats according to
# - needs for preparation before ingest
# - deletable formats
# - hint for appraisal
# This will then create in the directory which the program is running from
# (a) an excel spreadsheet with added columns for
#     Category, Deletion and Appraisal,
# (b) a csv-file with the file paths for all the files that are marked for deletion
# (c) a file with the file paths in a tag format that can afterwards be added to the json file that archifiltre 
#     (https://github.com/SocialGouv/archifiltre-docs) creates. If you want to use these tags you need to tell the
#     script how to shorten the file paths so archifiltre will be able to interpret them: 
#     The file paths in the archifiltre json start with the folder that is has been handed over for analysis to archifiltre.
#     In DROID the file paths are absolute. So for the file paths to work in archifiltre the folders leading 
#     up to the analyed folders have to be removed.
#     e.g. Let's say, in archifiltre the folder "archifolder" has been analysed, in DROID and in archifiltre.
#     "archifolder" is placed at /path/to/archifolder.
#     Then you need to give the script as input for prefix for archifiltre: "/path/to"
      

import pandas as pd
import numpy as np
import os
import json

# below loads the csv file into pandas and takes required columns, additional columns for multiple identification are not taken yet as this breaks the csv read. 
# It also asks for the archifiltre prefix and loads a copy of the format-list.csv
csvraw = input("Enter filepath of DROID csv to analyse: ")
csvraw = csvraw.strip('"')
columns_needed = ['ID','PARENT_ID','URI','FILE_PATH','NAME','METHOD','STATUS','SIZE','TYPE','EXT','LAST_MODIFIED','EXTENSION_MISMATCH','FORMAT_COUNT','PUID','MIME_TYPE','FORMAT_NAME','FORMAT_VERSION']
csv = pd.read_csv(csvraw, usecols=columns_needed, low_memory=False)
droidname = os.path.basename(csvraw)
droidname = droidname.rstrip('.csv')

archifiltre_prefix = input("Enter the prefix that has to be removed for the archifiltre json (If no archifiltre tags are"
                           " needed, you can leave this empty. Further info in the comment in the script.):")

# delimiter for this csv file is currently semicolon - if the csv is with commas (as the DROID output is) the delimiter parameter can be dropped)
formatlist = pd.read_csv('format-list.csv', delimiter=";")


def format_categorization():

    #Output file
    formatcat = pd.ExcelWriter(droidname + '_categorization.xlsx', engine='xlsxwriter')

    #entire droid file as input, adding "Category" columns (has to exist for condition checking)
    all = csv
    all.loc[3, 'Category'] = ''
      
    #establish lists according to column names in format-list.csv
    appraisalList = formatlist['appraisal hint'].values.tolist()
    unchangedList = formatlist['unchanged'].values.tolist()
    autoMigList = formatlist['automatic migration'].values.tolist()
    manMigList = formatlist['manual migration'].values.tolist()
    noOpenList = formatlist['cannot be opened'].values.tolist()
    deleteList = formatlist['delete'].values.tolist()
    protectedList = formatlist['password protected'].values.tolist()
    compressedList = formatlist['compressed'].values.tolist()
    researchList = formatlist['research started'].values.tolist()
    unknownList = formatlist['not categorized yet'].values.tolist()


    # Lists for generation of tags for archifiltre and as base for deletion script
    deletionList = []
    appraisalArchifiltreList = []

    # row by row: PUID is compared to labels in formatliste and assigned a Category
    for i in range(len(all)):
        # if row is not a Folder...
        if all.TYPE[i] != 'Folder':

            # formats that have not been identified are categorized
            if (all.loc[i, 'EXTENSION_MISMATCH']):
                all.loc[i, 'Category'] = 'Extension Mismatch'

            if all.loc[i, 'FORMAT_COUNT'] != 1:
                all.loc[i, 'Category'] = 'No reliable format id'

            # empty files are classed as deletable
            if all.loc[i, 'SIZE'] == 0:
                all.loc[i, 'Category'] = 'delete because empty'
                all.loc[i, 'Deletion'] = 'TRUE'
                delKand = all.loc[i, 'FILE_PATH']
                # print(delKand)
                deletionList.append(delKand)


            # all files with a puid that have not been categorized above are categorized according
            # to format-list.csv
            puid = all.loc[i, 'PUID']
            if (not pd.isna(puid) and pd.isna(all.loc[i, 'Category'])):

                if puid in appraisalList:
                    all.loc[i, 'Appraisal'] = 'appraisal hint'
                    appraisalKand = all.loc[i, 'FILE_PATH']
                    appraisalKand = str.replace(appraisalKand, '\\', '/')
                    appraisalKand = appraisalKand[len(archifiltre_prefix):]
                    appraisalKandFolder = appraisalKand[:appraisalKand.rfind('/')]
                    appraisalArchifiltreList.append(appraisalKand)
                    appraisalArchifiltreList.append(appraisalKandFolder)

                if puid in deleteList:
                    all.loc[i, 'Category'] = 'delete'
                    all.loc[i, 'Deletion'] = 'TRUE'
                    delKand = all.loc[i, 'FILE_PATH']
                    deletionList.append(delKand)
                elif puid in unchangedList:
                    all.loc[i, 'Category'] = 'unchanged'
                elif puid in autoMigList:
                    all.loc[i, 'Category'] = 'automatic migration'
                elif puid in manMigList:
                    all.loc[i, 'Category'] = 'manual migration'
                elif puid in noOpenList:
                    all.loc[i, 'Category'] = 'cannot be opened'
                elif all['PUID'][i] in protectedList:
                    all.loc[i, 'Category'] = 'password protected'
                elif puid in compressedList:
                    all.loc[i, 'Category'] = 'compressed'
                elif puid in researchList:
                    all.loc[i, 'Category'] = 'research started'
                elif puid in unknownList:
                    all.loc[i, 'Category'] = 'format not categorized'

    #formatting and output of XLSX-sheet
    categorybook = formatcat.book
    format = categorybook.add_format({
        'bold': True,
        'fg_color': '#4c9df7'})

    all.to_excel(formatcat, sheet_name='Kategorisierte Formate', index=False, startcol=0, startrow=1)
    sheet1 = formatcat.sheets['Kategorisierte Formate']
    # print(sheet1)
    sheet1.write('A1', 'Categorization of Formats')
    sheet1.write_row('B1:X1',['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
                              '', ''], format)
    formatcat.close()

    # generation of tags for archifiltre  
    appraisaltag = {"87c45fe4-c027-4c65-9594-fb4e0040a68c": { "ffIds": appraisalArchifiltreList,
                                                        'id': "87c45fe4-c027-4c65-9594-fb4e0040a68c",
                                                        "name": "Bewertungshinweise"

                                                        }
              }


    appraisaltag = json.dumps(appraisaltag, ensure_ascii=False)
    appraisaltag = appraisaltag.strip("{")
    appraisaltag = appraisaltag.strip("}")

    with open(droidname+"_archifiltre-tags.txt", "w", encoding='utf-8') as f:
        f.write(appraisaltag + '}')
          
    # generation of file with list of files that are to be deleted
    with open(droidname+"_delete.csv", "w", encoding='utf-8') as g:
        for i in deletionList:
            g.write(i + '\n')

format_categorization()


