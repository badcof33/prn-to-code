import sys
import re
import os
import argparse

## Create an object of the commad line options reader.
parser = argparse.ArgumentParser(description='Update dataset source code files based upton data found in an prn file.')

parser.add_argument('--prn-file', '-p', nargs=1, help='Name of release')
parser.add_argument('--code-file', '-c', nargs=1, help='Name of code file to update')
parser.add_argument('--include-file', '-i', nargs=1, help='Name of header file to update.')

args = parser.parse_args()

# Read the new data from a Excel export file
# Each line seperates its data elements with whitespace
# The symbol name and the data value copied into a dictionay as a pair of key/value.
with open(args.prn_file[0], 'r') as textInputHdl:
    textInput = textInputHdl.readlines()
newDatDict={}
newAddrDict = {}
for line in textInput:
    mc = re.search('^(?P<comment>;+)\s*(?P<rest>.*)$', line)
    if mc == None: # filter comment lines, starting with ';'
        md = re.search('^\s*(?P<addrhex>[0-9a-fA-F]+)\s+(?P<val>[0-9a-fA-F]+)\s+(?P<rest>.*)$', line)
        numberOfWords = len(md.group('rest').split())
        if md != None and numberOfWords == 1:
            key = md.group('rest')
            if not key in newDatDict:
                newDatDict[key] = int('0x'+md.group('val'), 16)
                newAddrDict[key] = int('0x'+md.group('addrhex'), 16)
            else:
                print "Multiple occurrence of '" + key + "'at", md.group('addrhex')
                exit(-1)

# READ CODE FILES AND UPDATE DATA
# -------------------------------
# Scan the code file for symbols and check if data needs update.
# If symbol is not found abort with error code. Keep original file unchanged.
# If the code files does not have an entry for a requested symbol name, abort with error code.
with open(args.code_file[0], "r") as codeInputHdl:
    codeInput = codeInputHdl.readlines()
index = 0
codeOutput = []
for codeLine in codeInput:
    mCode = re.search('^\s*\{\s*(?P<val>\d+)\s*,\s*(?P<min>\d+)\s*,\s*(?P<max>\d+)\s*\}.*//\s+(?P<addrdec>\d+)\s+-\s+(?P<rest>.*)$', codeLine)
    if mCode != None:
        index += 1
        currVal = int(mCode.group('val'))
        currValMin = int(mCode.group('min'))
        currValMax = int(mCode.group('max'))
        rest = mCode.group('rest').split()
        currName = rest[0]
        if currName in newDatDict:
            useVal = newDatDict[currName]
            newDatDict.pop(currName)
        else:
            useVal = currVal
        if currValMin <= useVal <= currValMax:
            codeOutput.append('\t{' + '{:>3}, {:>3}, {:>3}'.format(useVal, currValMin, currValMax) + "},    // " + str(index) + " - " + mCode.group('rest') +"\n")
            if useVal != currVal: print "Changing", currName, "from", currVal, "to", useVal
        else:
            print "Value for", currName, "out of bounds", currValMin, "...", currValMax
            exit(-2)
    else:
        codeOutput.append(codeLine)

if len(newDatDict) > 0:
    print "Found unassigned data:"
    for unassigned in newDatDict.keys():
        print " - ", unassigned

# No spare entry: Write output files
with open("_" + args.code_file[0], "w") as codeOutputHdl:
    codeOutput.append('\n#error Unassigned addresses (refer to comment below):\n')
    for unassigned in newDatDict.keys():
        codeOutput.append("/* - " + unassigned + " */\n")
    for line in codeOutput:
        codeOutputHdl.write(line)

# READ HEADER AND UPDATE ADDRESS
# ------------------------------
# Scan the include file for symbols and check if new address differes from new one.
# If symbol is not found abort with error code. Keep original file unchanged.
# If the code files does not have an entry for a requested symbol name, add it.
with open(args.include_file[0], "r") as includeInputHdl:
    includeInput = includeInputHdl.readlines()
index = 0
includeOutput = []
for includeLine in includeInput:
    mHeader = re.search('^\s*#define\s+(?P<name>[_0-9A-Z]+)\s+(?P<addrdec>\d+)\s+(?P<restOfLine>.*)$', includeLine)
    if mHeader != None:
        if mHeader.group('name') in newAddrDict:
            includeOutput.append("#define" +  mHeader.group('name') + mHeader.group('addrdec') +  '\t' +  mHeader.group('restOfLine'))
            newAddrDict.pop(mHeader.group('name'))
        else:
            includeOutput.append(includeLine)

if len(newAddrDict) > 0:
    print "Append unassigned addresses:"
    includeOutput.append('\n/* **** Unassigned addresses: **** */\n')
    for unassigned in newAddrDict.keys():
        includeOutput.append("#define " + unassigned + " " + newAddrDict[unassigned])
    print "No file changed."
with open("_" + args.include_file[0], "w") as includeOutputHdl:
    for line in includeOutput:
        includeOutputHdl.write(line)
