# ornl-modis-site-imgs

This is a simple hackathon example script that will build a library of modis
based images using [MYD09A1](https://lpdaac.usgs.gov/products/myd09a1v006/) and
[MOD09A1](https://lpdaac.usgs.gov/products/mod09a1v006/) for a set of target sites via
ORNL’s modis subsetting api. Basic QC filtering is done and a gamma correction
is applied to the images for better viewing. Filtered pixels are set as transparent
in the alpha channel.

See the site.csv example for defining site targets.

To add the python dependencies, a simple pip install can often work fine, e.g.:

```
$ pip3 install pandas requests Pillow scikit-image --user
```


Then run:

```
$ ./build_mod_imgs.py
```

Note, sites.csv must be in the working directory (see script) and outputs are
placed in ./site-imgs/\<site_tag\>/\<prod\>_A\<date\>_rgb.png

