from flirpy.io import Fff
from glob import glob
import cartopy.crs as ccrs
import matplotlib.pyplot as plt

if __name__ == "__main__":

    files = glob("/home/josh/data/flirpy_test/output/20181105_121443_IR/raw/*.fff")

    # N/W Lat/Lon
    coords = [Fff(frame).get_gps() for frame in files]

    lat, lon, alt, _, _ = coords.T
 
    #x, y = map.to_pixels(lat.m
    #ax = map.show_mpl(figsize=(8, 6))
    #ax.plot(x, y, 'or', ms=10, mew=2);

    # setup Lambert Conformal basemap.
    # set resolution=None to skip processing of boundary datasets.
    ax = plt.axes(projection=ccrs.PlateCarree())
    img_extent = (-120.67660000000001, -106.32104523100001, 13.2301484511245, 30.766899999999502)

    ax.stock_img()

    ax.plot(lon, lat,
         color='red',
         transform=ccrs.PlateCarree(),
         )

    plt.show()
