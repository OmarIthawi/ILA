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

## Remove the old trained database
iladbpath = path.join(scriptdir, 'ila-trained.db')
if path.exists(iladbpath):
    os.remove(iladbpath)

## Make new untrained database
copyfile(path.join(scriptdir, 'ila-untrained.db'), iladbpath)

## Connect to the database file
con = sqlite3.connect(iladbpath)
cursor = con.cursor()

# End: Initializtion

# Data Entry

## Read from the train.csv (Training Set) 
traincsv = open(path.join(scriptdir, 'train.csv'))
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

## Close the opened file (train.csv)
traincsv.close()


## Print everything from train.csv
print ','.join(titles)
for case in cases:
    print ','.join(case)
   
print '----'

## Insert the decisions into table decision
decisions = []
decquery = 'INSERT OR IGNORE INTO decision (name) VALUES (?);'
for case in cases:
    decision = case[len(case) - 1]
    if decision not in decisions:
        print decision, cursor.execute(decquery, [decision])
        decisions.append(decision)
        
 
      
print '----'

## Insert attributes, attribute_value, case, adjective
## i.e. insert everything else.

# Insert the titles (attributes)
titlequery = '''
            INSERT INTO attribute (name) VALUES (?);
'''

idx=0
for attribute in titles[:-1]:
    print attribute, cursor.execute(titlequery, [attribute])


# Insert the attribute_values
valquery   = '''INSERT INTO attribute_value 
                            (name, attribute_id) 
                            VALUES (?, (SELECT id 
                            FROM attribute
                                         WHERE name = ?));'''
                                         

idx=0
for attribute in titles[:-1]:
    
    values = {}
    caseid = 0
    for case in cases:
        caseid += 1
        decision = case[len(case) - 1]
        
        attrvalue = case[idx]
        if attrvalue not in values.keys():
            print attrvalue, cursor.execute(valquery, [attrvalue, attribute])
            values[attrvalue] = True

    idx+=1

# Insert the cases
casequery = '''INSERT INTO `case` (has_rule, decision_id)
                VALUES (0, (SELECT id 
                                     FROM decision WHERE name = ? ))'''

idx=0
for attribute in titles[:-1]:
    print '--'
    
    values = {}
    caseid = 0
    for case in cases:
        caseid += 1
        decision = case[len(case) - 1]
        if idx == 0:
            cursor.execute(casequery, [decision])
            print '<caseid>', caseid
    idx+=1

# Insert the adjectives (a person has attribute_value)
adjquery  = '''INSERT INTO adjective (case_id, attribute_value_id)
                VALUES (?, (SELECT id FROM attribute_value
                        WHERE name = ? 
                                   AND attribute_id = (
                        SELECT id FROM attribute
                                       WHERE name = ?)
                                   ))
                                                 '''
                                                 
                                                 
idx=0
for attribute in titles[:-1]:
    print '--'
    
    values = {}
    caseid = 0
    for case in cases:
        caseid += 1
        attrvalue = case[idx]
        
        adjargs = [str(caseid), attrvalue, attribute]
        print adjargs
        
        print cursor.execute(adjquery, adjargs)
        
    idx+=1

print '----'

# End: Data Entry

# Training

## Loop over the cases without a rule and try to generate one for 
def trainall():
    caseuntrainedquery = 'SELECT id, decision_id FROM `case` WHERE has_rule = 0'
    cursor.execute(caseuntrainedquery)
    case = cursor.fetchone()
    
    while case:
        combination = traincase(case)
        
        generalizerule(combination)
        
        cursor.execute(caseuntrainedquery)
        case = cursor.fetchone()
        
    print '\n' * 5
    print '-' * 10
    print 'Training is Complete...'
    print '-' * 10

def generalizerule(combination):
    print '\tGeneralizing', combination
    query = 'UPDATE `case` SET has_rule = 1 WHERE id = ?'

    for case in casesofcombination(combination):
        caseid = case[0]
        print '\t\tGeneralized:', caseid, cursor.execute(query, [caseid])
    

def casesofcombination(combination, 
                        execludedecisionid = None,
                        execludecaseid = None):
    """
    Get cases matching the combination.
    Returns cases as (id, decision_id, has_rule)
    
    Input combination e.g. (hair-color=brown) or 
    (hair-color=brown and eye-shape=wide) and so on
    
    Output: cases that matches the comination,
    
    There are two optional conditions:
        (execludedecisionid) to execlude certain cases based on the 
                             decision e.g. execlude all the Caucasians


        (execludecaseid) to execlude one case e.g. exelude case #5
    """
        
    whereparts = []
    joinparts = []
    params = []
    
    if execludedecisionid:
        whereparts.append('c.decision_id != ?')
        params.append(execludedecisionid)
        
    if execludecaseid:
        whereparts.append('c.id != ?')
        params.append(execludecaseid)

    idx = 0
    for attribute_value_id in combination:
        idx += 1
        
        joinparts.append('''INNER JOIN adjective AS ad%s
                           ON ad%s.case_id = c.id''' % (idx, idx))
        
        whereparts.append('ad%s.attribute_value_id = %s' % (idx, '?'))
        
        params.append(attribute_value_id)
        
    
    checkquery = '''SELECT c.id, c.decision_id, c.has_rule
                        FROM `case` AS c
                        %s
                        WHERE %s
                        ''' % (
                            '\n'.join(joinparts), 
                            ' AND '.join(whereparts)
                             )
    
    cursor.execute(checkquery , params)
    all = cursor.fetchall()
    return all



def traincase(case):
    """
    Train the Database on single Case.
    
    Input = a Case (with no rule yet) among Data Set
    Output = a Rule
    """
    
    caseid = case[0]
    decisionid = case[1]
    
    ## Get the case adjectives (specifications)
    cursor.execute('''SELECT attribute_id, attribute_value_id
                      FROM adjective 
                      INNER JOIN attribute_value 
                        ON attribute_value_id = attribute_value.id
                      WHERE case_id = ?''', [caseid])
    
    print 'Case:', case
    
    data = list(cursor.fetchall())
    attribute_value_ids = map(lambda row: row[1], data)
    
    
    ## Loop over all combination depthes = one by one, each two, each 
    ## three and so on
    for depth in range(1, len(attribute_value_ids) + 1):
        ## Combination is a combination
        ## Get all possible combinations of that depth
        for combination in combinations(attribute_value_ids, depth):
            
            ### For example for combination (hair-color=blond) and the 
            ### (decision=Caucasian) this would mean
            ### Get me all the cases that has (hair-color=blond) and 
            ### decision is not Caucasian, if no results found then
            ### we conclude that (hair-color=blond) is a 
            ### distinguishing feature of the Caucasian race, hence
            ### it is a rule
             
            matchingcases = list(casesofcombination(combination,
                    execludecaseid = caseid,
                    execludedecisionid = decisionid))
                    
            
            # If no results were found, it is a rule
            isrule = (len(matchingcases) == 0)
            
            if isrule:
                print '\tRule, C:', combination

                ### Insert the rule in the database
                rulequery = 'INSERT INTO rule (decision_id) VALUES (?)'
                condquery = '''INSERT INTO
                                `condition` (rule_id, attribute_value_id) 
                                VALUES (?, ?)'''

                cursor.execute(rulequery, [decisionid])
                ruleid = cursor.lastrowid
                
                for attribute_value_id in combination:
                    cursor.execute(condquery, [ruleid, attribute_value_id])
                    
                return combination
                    
            else:
                print '\tNot Rule, C:', combination
    
    print 'Cannot Train, Contradictory Information was Found'
    print case
    exit(1)

def printrules():
    print '\n' * 3, 'Rules:'
    
    cursor.execute('''SELECT r.id, d.name 
                      FROM rule as r
                      INNER JOIN decision AS d
                        ON d.id = r.decision_id
                      ORDER BY r.decision_id''')
                        
    for ruleid, dname in cursor.fetchall():
        
        cursor.execute('''SELECT at.name, av.name 
                          FROM `condition` AS c
                          INNER JOIN attribute_value AS av
                            ON av.id = c.attribute_value_id
                          INNER JOIN attribute AS at 
                            ON at.id = av.attribute_id
                          WHERE c.rule_id = ?''', [ruleid])
        
        conditions = []
        for atname, avname in cursor.fetchall():
            conditions.append('%s=%s' % (atname, avname))
        
        
        print '\tRule #%s' % ruleid, ' and '.join(conditions),
        print ' ->', dname
    
trainall()
printrules()

con.commit()
con.close()

