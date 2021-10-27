# ornl-modis-site-imgs

A simple example script for a hackathon that will build a library of modis
based site images via ORNL’s modis subsetting api.

See the site.csv example for defining site targets. Note, you need to add a
legitimate email in the csv file. Also, the site_tag can only be 8 characters or less.

To add the python dependencies, a simple pip install can often work fine, e.g.:

```
$ pip3 install pandas --user
$ pip3 install requests --user
```
