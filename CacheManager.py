import os
from shutil import rmtree
from sys import getsizeof
from csv import DictReader
from zlib import compress
from pickle import load, dumps
from threading import Thread
from requests import Session, models
from urllib.parse import quote

MAX_CACHE_SIZE = int(18.5 * 1024 ** 2)          # 18.5 MB limit for both disk and in-memory cache
AVAILABLE_DNSSERVER_DISK = int(13 * 1024 ** 2)  # 13 MB limit for disk cache (i.e., /cache/)
MAX_RANK_PICKLE_FILE_ARTICLE = 215    # pickle file limited to articles 1 thru 214
MAX_RANK_PARTIAL_CACHE_ARTICLE = 358  # partial /cache/ limited to articles 215 thru 357

DEFAULT_CACHE_DIR = "/cache"
DNS_DIR = "dns_server"
HTTP_DIR = "http_server"
DEFAULT_ORIGIN = "cs5700cdnorigin.ccs.neu.edu"
DEFAULT_PORT = "8080"
DEFAULT_PAGE_VIEWS_CSV = "pageviews.csv"                   # default name for pageviews csv
DEFAULT_PICKLE_FILE = "serialized_in_memory_cache.pickle"  # default name for pickle file

class CacheManager:
    """
    CacheManager is used to handle all caching related tasks. In particular, CacheManager's
    functionality can be decomposed into two categories:
        1. Static Methods: These methods involve creating caches during deployment (deployCDN);
            in particular, CacheManager.buildInMemoryCache() creates and writes a pickle file
            to disk (a serialized Python dictionary that is later read into memory by httpserver),
            and CacheManager.buildPartialDiskCache() creates a cache of compressed articles in a 
            /cache/ folder that is approximately 13 MB in size (AVAILABLE_DNSSERVER_DISK).
        2. Class Methods: These methods are used by a CacheManager object that is used by httpserver;
            in particular, the httpserver first tells the CacheManager object to load the pickle file
            into its memory before deleting the pickle file; then, all subsequent GET requests made to
            HTTP server will cause httpserver to ask the CacheManager object if it has the requested 
            article in-memory - if it the requested article is not in-memory nor in /cache/ (cache miss), 
            then httpserver asks CacheManager to download the article for it.
    """
    
    def __init__(self, 
            origin_url: str = DEFAULT_ORIGIN, 
            port: str = DEFAULT_PORT,
            cache_dir: str = DEFAULT_CACHE_DIR):
        """
        Purpose: Instantiates a new CacheManager object with an origin server URL and port,
                 as well as a preferred cache directory folder name.
        :param origin_url: str representing the URL of the origin server.
        :param port: str representing the port number of the origin server.
        :param cache_dir: str representing the desired name of the on-disk cache directory.
        """
        self.origin = "http://" + origin_url + ":" + port 
        self.cache_dir = os.path.join( os.getcwd(), HTTP_DIR, "cache" )
        self.session = Session()        
        self.in_memory_cache = dict()
        self.available_memory = MAX_CACHE_SIZE
        self.available_disk = MAX_CACHE_SIZE

    def getUrlResponse(self, url: str) -> models.Response:
        """
        Purpose: Takes in a URL that has been parsed and formatted by httpserver, and then
                 returns its content.
        :param url: str representing the web content to fetch.
        :return: models.Response object representing the HTML of the requested URL.
        """
        return self.session.get(url)

    def loadInMemoryCache(self, pickle_file: str = DEFAULT_PICKLE_FILE) -> None:
        """
        Purpose: Loads the pickle file into memory. More specifically, the pickle file is a serialized
                 Python dictionary object; this file can therefore be read into memory (i.e., the 
                 CacheManager object's self.in_memory_cache dictionary attribute). Once the pickle file
                 is read into memory, it is deleted so that other files can be cached on disk hereafter.
        :param pickle_file: str representing the name of the pickle file in the immediate directory. 
        :return: Void.
        """
        pickle_file_path = os.path.join(os.getcwd(), HTTP_DIR, pickle_file)
        if not os.path.exists(pickle_file_path):  # just in case pickle file does not exist
            return
        with open(pickle_file_path, "rb") as f:
            compressed_content_dict = load(f)
        for url, compressed_content in compressed_content_dict.items():
            self.in_memory_cache[url] = compressed_content
        self.available_memory -= getsizeof(self.in_memory_cache)
        os.remove(pickle_file_path)  # free up disk memory now that pickle is in-memory

    def completeDiskCacheThread(self) -> None:
        """
        Purpose: Spawns a new daemon thread just before httpserver calls "server_forever()"; 
                 this allows httpserver to serve requests while simultaneously running the 
                 CacheManager.completDiskCache() method (see that method below).
        :return: Void.
        """
        t = Thread(target=self.completeDiskCache)
        t.daemon = True
        t.start()

    def completeDiskCache(self, page_views_csv: str = DEFAULT_PAGE_VIEWS_CSV) -> None:
        """
        Purpose: When httpserver is called, it must immediately start serving requests;
                 while the DNS server is scp 14MB of /cache/ to httpserver's disk, it
                 is up to httpserver to download the other 7MB into /cache/. To do this,
                 this method downloads 7MB of compressed files to /cache/ that are
                 disjoint with the files in the 14MB /cache/ file and disjoint with the
                 compressed files in httpserver memory.
        :param page_views_csv: str representing the name of the "pageviews.csv" file.
        :return: Void.
        """
        self.available_disk = MAX_CACHE_SIZE - AVAILABLE_DNSSERVER_DISK 
        if not os.path.exists(self.cache_dir):
            os.mkdir(self.cache_dir) 
        page_views_csv_path = os.path.join( os.getcwd(), HTTP_DIR, page_views_csv )
        if not os.path.exists(page_views_csv_path):
            return
        with open(page_views_csv_path, "r") as csv_file:
            reader = DictReader(csv_file)
            for item in reader:
                if int(item["ranks"]) < MAX_RANK_PARTIAL_CACHE_ARTICLE:
                    continue
                article = quote(item["article"].replace(" ", "_"))
                request_url = self.origin + "/" + article
                if (article in self.in_memory_cache # already in memory
                        or os.path.exists(self.cache_dir + "/" + article)):  # already on disk
                    continue
                response = self.session.get(request_url)
                if response.status_code not in range(200, 300):
                    # print(f"***BAD STATUS CODE -> {request_url}")
                    continue
                compressed_content = compress(response.content)
                if self.available_disk - len(compressed_content) > 0:
                    with open(self.cache_dir + "/" + article, "wb+") as f:
                        f.write(compressed_content)
                    self.available_disk -= len(compressed_content)
                else:
                    break

    @staticmethod
    def buildPartialDiskCache(origin_url: str = DEFAULT_ORIGIN,
            port: str = DEFAULT_PORT,
            page_views_csv: str = DEFAULT_PAGE_VIEWS_CSV,
            cache_dir: str = DEFAULT_CACHE_DIR) -> None:
        """
        Purpose: This static method is run on the DNS server during deployment (deployCDN);
                 the purpose of this method is to create a 14MB /cache/ folder of compressed
                 popular pages (according to pageviews.csv) - pages which are disjoint from
                 the ones in the pickle file. When the CDN is run (runCDN), this folder is
                 scp over to all 7 HTTP servers, whereupon DNS's copy of /cache/ is removed.
        :param origin_url: str representing the address of the origin server.
        :param port: str representing the port number of the origin server.
        :param page_views_csv: str representing the name of the pageviews.csv file, which
                should be in the immediate directory.
        :param cache_dir: str representing name of /cache/ directory.
        :return: Void.
        """
        cache_dir = os.path.join( os.getcwd(), DNS_DIR, "cache")
        if os.path.exists(cache_dir):
            rmtree(cache_dir)
        os.mkdir(cache_dir)
        origin = "http://" + origin_url + ":" + port
        available_disk = AVAILABLE_DNSSERVER_DISK
        session = Session()
        with open(os.path.join( os.getcwd(), DNS_DIR, page_views_csv ), "r") as csv_file:
            reader = DictReader(csv_file)
            for item in reader:
                if int(item["ranks"]) < MAX_RANK_PICKLE_FILE_ARTICLE:
                    continue
                article = quote(item["article"].replace(" ", "_"))
                request_url = origin + "/" + article
                response = session.get(request_url)
                if response.status_code not in range(200, 300):
                    # print(f"***BAD STATUS CODE -> {request_url}")
                    continue
                compressed_content = compress(response.content)
                if available_disk - len(compressed_content) > 0:
                    with open(os.path.join( cache_dir, article ), "wb+") as f:
                        f.write(compressed_content)
                    available_disk -= len(compressed_content)
                else:
                    break
        session.close()
    
    @staticmethod
    def buildInMemoryCache(origin_url: str = DEFAULT_ORIGIN,
            port: str = DEFAULT_PORT,
            page_views_csv: str = DEFAULT_PAGE_VIEWS_CSV,
            pickle_file: str = DEFAULT_PICKLE_FILE) -> None:
        """
        Purpose: To be run on the DNS server at deployment (deployCDN);
                this static method is used to download 18.5MB worth of the compressed top 
                articles according to pageviews.csv; as these articles are downloaded from
                the origin server, they are placed into a Python dictionary; once the 
                dictioanry hits 18.5MB in size, it is serialized and written to a pickle
                file, to be scp to HTTP servers and read into their memories at runtime.
        :param origin_url: str representing the address of the origin server.
        :param port: str representing the port number of the origin server.
        :param page_views_csv: str representing the name of the pageviews.csv file, which
                should be in the immediate directory.
        :param pickle_file: str representing the desired name of the pickle file.
        :return: Void.
        """
        origin = "http://" + origin_url + ":" + port
        available_memory = MAX_CACHE_SIZE
        session = Session()
        in_memory_cache = dict() 
        with open(os.path.join( os.getcwd(), DNS_DIR, page_views_csv ), "r") as csv_file:
            reader = DictReader(csv_file)
            for item in reader:
                article = quote(item["article"].replace(" ", "_"))
                request_url = origin + "/" + article
                response = session.get(request_url)
                if response.status_code not in range(200, 300):
                    # print(f"***BAD STATUS CODE -> {request_url}")
                    continue
                compressed_content = compress(response.content)
                if available_memory - len(compressed_content) > 0:
                    in_memory_cache[article] = compressed_content
                    available_memory -= len(compressed_content)
                else:
                    break 
        session.close()
        serialized_in_memory_cache = dumps(in_memory_cache)
        in_memory_cache.clear()
        with open(os.path.join( os.getcwd(), DNS_DIR, pickle_file ), "wb") as f:
            f.write(serialized_in_memory_cache)

