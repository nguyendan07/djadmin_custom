# How to do things with Django admin?

## Get it up and running
**Install pipenv and create virtual environments**
```
pip install -U pip pipenv
pipenv install
pipenv shell
```

**Running project**
```
./manage.py migrate
./manage.py loaddata dev_data.json
./manage.py runserver
```
*Open in your browser and login to /admin with admin/123456a@*
