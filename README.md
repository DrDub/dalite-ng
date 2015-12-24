Dalite NG
=========

Dalite NG is a rewrite of the [Dalite tool][old-dalite] as a cleaner, Django-based LTI
tool.

[old-dalite]: https://github.com/open-craft/edu8-dalite/

Setting up the development server
---------------------------------

1. Install the requirements (you probably want to set up a virtualenv first).

        $ pip install -r requirements.txt

2. Set up the database connection.  The default configuration is to use the
   MySQL database `dalite_ng` and the user `dalite`.  To set up the database,
   run these commands as the MySQL superuser:

        mysql> CREATE DATABASE dalite_ng;
        mysql> CREATE USER 'dalite' IDENTIFIED BY 'your password here';
        mysql> GRANT ALL PRIVILEGES ON dalite_ng.* TO dalite;

   The password can be passed in the environment:

        $ export DALITE_DB_PASSWORD='your password here'

   Or to use sqlite3, set in local_setting.py a line containing

   DATABASES = { 'default' : { 'ENGINE' :  'django.db.backends.sqlite3', 'NAME': 'dalite_ng.sqlite3' } }

3. Generate a secret key, e.g. using `tools/gen_secret_key.py`, an put it in
   `dalite/local_settings.py`.

4. Create the database tables and the superuser.

        $ ./manage.py migrate
        $ ./manage.py createsuperuser

5. Run the Django development server.

        $ ./manage.py runserver

Running the tests
-----------------

The tests can be run with

    $ make test

After the tests have finished, you can view the coverage report using:

    $ make coverage-report

Attributions
------------

The thumbs up and down icons were taken from the [Entypo pictograms by Daniel
Bruce][entypo].

[entypo]: http://www.entypo.com/
