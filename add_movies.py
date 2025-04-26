import sqlite3

conn = sqlite3.connect('database.db')
c = conn.cursor()

movies = [
    ('Inception', 'Sci-Fi', 'A thief who steals corporate secrets through dream-sharing technology.'),
    ('Titanic', 'Romantic', 'A love story aboard the doomed RMS Titanic.'),
    ('The Conjuring', 'Horror', 'Paranormal investigators help a family terrorized by a dark presence.'),
    ('The Avengers', 'Action', 'Earth’s mightiest heroes unite to fight a global threat.')
]

for title, genre, desc in movies:
    c.execute('INSERT INTO movies (title, genre, description) VALUES (?, ?, ?)', (title, genre, desc))

conn.commit()
conn.close()
