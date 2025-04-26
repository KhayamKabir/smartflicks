import sqlite3
import csv

conn = sqlite3.connect('database.db')
c = conn.cursor()

with open('movies.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        c.execute('''
            INSERT INTO movies (title, genre, description, rating)
            VALUES (?, ?, ?, ?)
        ''', (row['title'], row['genre'], row['description'], float(row['rating'])))

c.execute('''
    SELECT COUNT(*) FROM movies WHERE title = ? AND genre = ? AND description = ? AND rating = ?
''', (row['title'], row['genre'], row['description'], float(row['rating'])))
if c.fetchone()[0] == 0:
    c.execute('''
        INSERT INTO movies (title, genre, description, rating)
        VALUES (?, ?, ?, ?)
    ''', (row['title'], row['genre'], row['description'], float(row['rating'])))


conn.commit()
conn.close()

print("Movies imported successfully!")
