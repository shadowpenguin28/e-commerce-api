**Setup Instructions**
- Install prerequisites via **requirements.txt**
- Clone git repository
- Run the following commands
  ```
  <activate virtual environment>
  pip install requirements.txt

  python manage.py makemigrations
  python manage.py migrate

  python manage.py createsuperuser
  => Add details

  python manage.py runserver
  ```

 Go to admin page and add 'shopkeeper' role to the superuser

 Then test the api by replacing the credientials or adding new data.

Use the docs on postman =>
https://documenter.getpostman.com/view/48733120/2sB3QCTDyz
