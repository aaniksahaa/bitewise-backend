## Create New Database in DBeaver

1. **Open DBeaver** and connect to your local PostgreSQL server
2. **Create a new database:**
   - Right-click on your PostgreSQL connection listed on left like 'bitewise_dev'
   - select Databases, then right click -> create new db
   - Enter database name (e.g., `bitewise_test`)
   - Click "OK"

## Test on cmd if it works

1. run commands like

psql conn_string

psql postgresql://bitewise:BITEWISE321@localhost:5432/bitewise_dev
psql postgresql://bitewise:BITEWISE321@localhost:5432/bitewise_test
psql postgresql://bitewise:BITEWISE321@localhost:5432/bitewise_test_1

2. in the hash console, check all table names with \dt, initially it will show no relations

## Update env

If things work, 

Edit your existing `.env` file and change the database name:
```env
LOCAL_DATABASE_URL=postgresql://bitewise:BITEWISE321@localhost:5432/bitewise_test
```

in terminal write 

source .env && echo $LOCAL_DATABASE_URL


## setup the db schema

1. run 
python fix-length.py
python alembic-check.py

and see whether things are fine, if ok, 

alembic upgrade head

then check

alembic current

## Load the seed data

Now run the seed scripts

python seed_users.py
python seed_dish_ingreds.py

