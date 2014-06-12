README


Inductive Learning  Program

File Structure:
readme.txt
ila.py
ila-trained.db
test.csv

Steps:
1)use SQlite to open ila-trained.db
2)run 'python ila.py' to check the hypothesis(rules)



Code Review:
ila.py imports training dataset from csv file. It uses SQLite database and sqlite3 module in python to malipulate tables and implement the ILA algorithm. It returns weather inductive result matches the class in testing dataset.If it matches it returns 'Correct' else it returns 'Incorrect' . 
