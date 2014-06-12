#!/usr/bin/python
# coding=utf-8

import sqlite3
import sys
import os, os.path as path
from itertools import combinations
from subprocess import call
from shutil import copyfile

# Initialization
scriptdir = path.dirname(path.realpath(__file__))

iladbpath = path.join(scriptdir, 'ila-trained.db')

con = sqlite3.connect(iladbpath)
cursor = con.cursor()

# End: Initializtion

# Data Entry

## Read from the train.csv (Training Set)
traincsv = open(path.join(scriptdir, 'test.csv'))
lines = traincsv.readlines()

## A function to parse (interpret or reading from) a line from csv file
def lineparse(line):
    line = line.strip()
    
    ### Convert TAB to Comma
    line = line.replace('\t', ',')
    
    ### Split the line into words based on comma
    parts = map(lambda s: s.strip(), line.split(','))
    
    return parts

titles = lineparse(lines[0]) ## The first line is only titles
cases = map(lineparse, lines[1:]) ## The rest of lines are the data


#print cases

## Close the opened file (train.csv)
traincsv.close()


cursor.execute('''SELECT r.id, d.name
FROM rule as r
INNER JOIN decision AS d
ON d.id = r.decision_id
ORDER BY r.decision_id''')

rules = []

for ruleid, dname in cursor.fetchall():
    
    cursor.execute('''SELECT at.name, av.name
		      FROM `condition` AS c
		      INNER JOIN attribute_value AS av
		      ON av.id = c.attribute_value_id
		      INNER JOIN attribute AS at
		      ON at.id = av.attribute_id
		      WHERE c.rule_id = ?''', [ruleid])
    
    conditions = {}
    for atname, avname in cursor.fetchall():
        conditions[atname] = avname
    
    rules.append({
        "id": ruleid,
        "decision": dname,
        "conditions": conditions
    })

#for index in rules:
#	print index

#exit()


def casedict(case):
    decision = case[len(case)-1]
    case = case[:-1]
    
    mappedcase = {}
    
    for i in range(len(case)):
        mappedcase[titles[i]] = case[i]
    
    return mappedcase, decision


idx = 0
for case, decision in map(casedict, cases):
    idx += 1
# case is list of dictionaries for all tuples
# decision is list of decisions
    applyingrule = None
    for rule in rules:
        
        applies = True
        for condattr, condattrvalue in rule["conditions"].iteritems():
            applies = applies and (
                case[condattr] == condattrvalue
            )
            
            if not applies:
                break # cond loop
        
        if applies:
            applyingrule = rule
            break # rule loop
    
    if applyingrule:
        iscorrect = (applyingrule['decision'] == decision)
        print "Test case #" + str(idx), "has rule #" + str(applyingrule['id'])
        print "\t> Induced decision is", applyingrule['decision']
        print "\t> Assumed decision is", decision
        
        if iscorrect:
            print "\t> Decision is correct"
        else:
            print "\t> Decision is NOT correct"
    else:
        print "Test case #" + str(idx), "has no rule"
        print "\t> Assumed decision is", decision

con.commit()
con.close()
