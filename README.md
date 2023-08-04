# Custom CDN

This repository contains Python code, bash scripts, and csv files for a complete [content delivery network (CDN)](https://en.wikipedia.org/wiki/Content_delivery_network). 

Please find a demo video of this program [linked here](https://youtu.be/wZDAvp1cLME).

Concepts covered in this project include (but are not limited to) CDNs, DNS, HTTP, bash scripting, network performance measurement and optimization, system design and optimization, cloud infrastructure and deployment, cache management, etc.

Tested on Ubuntu 20.04.1.

## Background

Before delving into the details of this project, it is important to first understand the following terms...

- <ins>Content Delivery Network (CDN)</ins>: A globally distributed network of servers that work together to deliver web content (images, video, etc.) to end-users in an efficient and reliable manner. A well-designed CDN reduces latency and improves performance of content delivery by serving the requested content from an edge server that is "closest" to the end-user (recall that because IP is overlaid on top of phyical fiber topology and is therefore an overlay network, the edge server that provides an end-user the best performance is not necessarily the edge server physically closest to that end-user). CDNs can also help reduce the load on origin servers by implementing well-designed caching mechanisms to cache popular content on edge servers which are located closer to end-users.
  - For example, consider Netflix's CDN. When a Netflix user wants to watch a show, they first send a DNS request to www.netflix.com. The request is then routed to the "closest" Netflix edge server based on that user's location, and then the user requests the content from that edge server. Each edge server caches popular content so that some content can be served directly from cache, thus improving overall performance and reducing the load on the origin server.
- <ins>Origin Server</ins>: The main server that hosts all of the original content. When a user requests a resource from an edge server, the edge server first sees if it already has a cached copy of that resource. If it does not, the edge server retrieves it from the origin server.
  - For example, if a Netflix user requests an episode of a show from an edge server, the edge server will first see if it has that episode in cache. If it does not, it will have to ask the origin server for that content. 
  - In this project, the origin server is [`cs5700cdnorigin.ccs.neu.edu:8080`](http://cs5700cdnorigin.ccs.neu.edu:8080/).
- <ins>Domain Name System (DNS)</ins>: A naming system used to map domain names to IP addresses, like phonebook for the Internet. More specifically, DNS is a hierarchical, distributed naming system that is used to translate human-readable domain names (e.g. "www.google.com") into the IP addresses that computers use to identify each other on the Internet. 
- <ins>DNS Server</ins>: A server that stores DNS records and responds to DNS queries to translate domain names into IP addresses.
  - For example, when a Netflix user first attempts to access www.netflix.com, they first send a DNS query to a recursive DNS resolver (typically a server provided by their ISP). Eventually their query is routed to Netflix's IP address, where its DNS server will determine which edge server to refer the user to (e.g., Netflix's DNS server refers a user in Lexington, MA to its edge server in Boston, MA).
- <ins>HTTP Server</ins>: A server that responds to HTTP requests, typically by returning web pages and other resources to the client that made the request.
  - In this project, the HTTP servers are edge servers, responsible for returning requested content and caching content from the origin server.

## Detailed Project Synopsis 

- *The overall goal of the CDN is to minimize average content download time.* This project contains a custom CDN using cloud servers. This project uses the pre-prepared origin server; this project utilizes 7 replica servers that are geographically distributed worldwide (the HTTP server locations), along with a system to determine theoptimal client-HTTP server mapping (the DNS server), where client requests are made from locations around the world.
- To simulate real-world tradeoffs when caching (i.e., to prevent servers from caching all of the contents of the origin server), a 20 MB limit on disk cache and in-memory cache is imposed on the DNS server and all HTTP servers. Moreover, because the organizations who design CDNs have an idea about the distribution of the varying popularities of their content (and can therefore adjust their caching mechanisms accordingly), the relative popularities of each page stored in the origin server are given as well. In particular, the file `pageviews.csv` provides a distribution/ranking of each page's popularity by total number of views; this distribution follows a [Zipfian distribution](https://en.wikipedia.org/wiki/Zipf%27s_law).
- This project also uses a limited amount of Python libraries so that the CDN is built nearly from scratch; libraries used include `dnslib`, [MaxMind's](https://en.wikipedia.org/wiki/MaxMind) `geopy2.webservice`, `BaseHTTPRequestHandler` from `http.server`, and `ThreadingMixIn` from `socketserver`.
- The locations of the servers are as follows:
  - The origin server contains HTTP content and is located at [`cs5700cdnorigin.ccs.neu.edu:8080`](http://cs5700cdnorigin.ccs.neu.edu:8080/).
  - The DNS server is located at `cdn-dns.5700.network`.
  - Each of the 7 HTTP servers were located at `cdn-http1.5700.network` through `cdn-http7.5700.network`; they were distributed around the world.
- Please see a visual overview of the project's architecture below:
<p align="center">
  <img src="https://github.com/alex-w-99/Custom-CDN/blob/main/Images/Custom_CDN_Architecture.png" width="800">
</p>

## Implementation Details

- <ins>`pageviews.csv`</ins>: A csv file which contains each page that is available on the origin server, its popularity by total views, and its ranking by total views. As mentioned in the **Detailed Project Synposis**, the distribution of views given in this csv file follows a [Zipfian distribution](https://en.wikipedia.org/wiki/Zipf%27s_law)
- <ins>`dnsserver`</ins>: An executable Python file containing the multi-threaded DNS server program. The DNS server accepts DNS query type A (i.e., IPv4 requests). It first determines the location of the client's IP address - the DNS server first attempts to use [MaxMind](https://en.wikipedia.org/wiki/MaxMind) `geoip2.webservice` library/service to do this; however, if MaxMind denies the DNS server's request, the DNS server uses `GeoInfo.py` to determine the client IP's location (see below). In either case, that client IP address's location is cached, and `GeoInfo.py` is used once again to determine the geographically closest HTTP server to the client, and that corresponding HTTP server's IP address is returned to the client.
  - The DNS server can be called on the command line using `./dnsserver -p <port> -n <name>`. For example, `./dnsserver -p 20090 -n cs5700cdn.example.com`.
- <ins>`GeoInfo.py`</ins>: This file is used by the DNS server to (1) find the geographic location of a given client IP address (although this functionality is really just a back up in case MaxMind fails/denies our request), and (2) determine which HTTP server is geographically closest to a given client (based on the client's geographic location, which is itself determined from their IP address).
- <ins>`ip.csv`</ins>: A csv file used by `GeoInfo.py` which contains mappings of IPv4 blocks to the countries in which IP addresses falling in this range most likely exist. This data was downloaded from MaxMind, and is slightly less reliable than their `geoip2.webservice` service. 
- <ins>`coordinates.csv`</ins>: A csv file used by `GeoInfo.py` which contains mappings of countries to their average coordinates. 
- <ins>`httpserver`</ins>: An executable Python file containing a multi-threaded HTTP server program. When the HTTP server is initially starts up at runtime, it begins downloading 7 MB of compressed origin server page content to its `/cache/` on-disk storage (to complement the 13 MB of compressed file content being `scp` from the DNS server to each HTTP server; the 7 MB of content that it downloads is disjoint from the 13 MB it is receiving!) The HTTP server accepts an HTTP GET request, and first determines if the requested page exists in its in-memory cache (i.e., a Python dictionary), decompressing it and returning it if so; if it is an in-memory cache miss, the HTTP server will then check if the requested page exists in its on-disk cache, decompressing it and returning it if so; if it is an on-disk cache miss, it will then fetch the content from the origin server and return it. 
  - The HTTP server can be called on the command line using `./httpserver -p <port> -o <origin>`. For example, `./httpserver -p 20090 -o cs5700cdnorigin.ccs.neu.edu:8080`.
- <ins>`CacheManager.py`</ins>: A Python file that helps manage caching, used on both the DNS server (during deployment) and on the HTTP servers (at runtime).
- <ins>`utils.py`</ins>: A simple utilities Python file that contains helper functions for `httpserver`.
- <ins>`build_in_memory_cache`</ins>: An executable Python file to be run at deployment; this program uses `CacheManager.py` to create a Python dictionary of up to size 18.5 MB that contains origin server page names to compressed content pairings, serializes that Python dictionary, and then writes that serializes Python dictionary (a "pickle" file) to the immediate directory. Later, when HTTP servers start up, this serialized Python dictionary is read into memory and deleted from the disk.
- <ins>`build_partial_disk_cache`</ins>: An executable Python file to be run at deployment; this program uses `CacheManager.py` to create a folder called `/cache/` on the DNS server's disk which contains up to 13 MB of compressed origin server page files (in such a way that the pages in `/cache/` are disjoint from the pages written to a serialized Python dictionary by `build_in_memory_cache`). Later, at runtime, the entire `/cache/` folder will be copied over to each HTTP server's disk, before it is deleted off of the DNS server's disk.
- <ins>`deployCDN`</ins>: A script which deploys the CDN. Deploying the CDN involves: (1) using `scp` to copy `httpserver` and all files used by `httpserver` over to each HTTP cloud server, as well as using `pip install` to ensure necessary Python libraries are installed on the HTTP cloud server, (2) using `scp` to copy over `build_in_memory_cache` and `build_partial_disk_cache` onto the DNS cloud server, (3) running `build_in_memory_cache` to create a "pickle" file, (4) using `scp` to copy that "pickle" file to each HTTP cloud server, (5) deleting the pickle file from the DNS server disk, (6) running `build_partial_disk_cache` to create the 13 MB `/cache/` folder on the DNS cloud server's disk, and (7) using `scp` to copy `dnsserver` and all other files used by `dnsserver` to the DNS cloud server. Please see the **Using and Testing CDN** section below for details on using this script. 
- <ins>`runCDN`</ins>: A script which runs the CDN. Running the CDN involves: (1) using `ssh` to run `httpserver` in the background on each HTTP cloud server, (2) using `scp` to copy the 13 MB `/cache/` folder over to each HTTP cloud server, (3) removing the `/cache/` folder from the DNS cloud server disk, and (4) using `ssh` to run `dnsserver` in the background on the DNS cloud server. Please see the **Using and Testing CDN** section below for details on using this script. 
- <ins>`stopCDN`</ins>: A script which stops the CDN. Stopping the CDN involves: (1) using `ssh` to (a) kill the `httpserver` background process on each of the 7 HTTP cloud servers and (b) remove all files from each HTTP cloud server, and (2) using `ssh` to (a) kill the `dnsserver` background process on the DNS cloud server and (b) remove all files from the DNS cloud server. Please see the **Using and Testing CDN** section below for details on using this script. 

## Using and Testing CDN

- <ins>Deploying the CDN</ins>: To run this script and deploy the CDN, use the command `./deployCDN -p <port> -o <origin> -n <name> -u <username> -i <keyfile>`. Please see **Implementation Details** above for details on what exactly this script does. 
- <ins>Running the CDN</ins>: To run this script and run the CDN, use the command `./runCDN -p <port> -o <origin> -n <name> -u <username> -i <keyfile>`. Please see **Implementation Details** above for details on what exactly this script does. 
  - To ensure that `dnsserver` and `httpserver` are all up and running, `ssh` into each server, use command `ps aux | grep python`, and locate the process attributed to the user that you `ssh`'d into the server as.
  - To ensure that the 20 MB disk quota is not exceeded on any server, `ssh` into each server, use the command `du -sh *`, and ensure that the sum of each file and folder contains less than 20 MB of data.
- <ins>Testing the CDN</ins>: To test the CDN, the CDN must first be deployed and run. After that, its two components must be tested separately:
  - <ins>Testing `dnsserver`</ins>: Once an HTTP server is up and running, it can be tested using a simple `dig` statement. For example, if the DNS server were running on my local machine on port 20090, the DNS server could be tested via the command `dig @127.0.0.1 -p 20090 cs5700cdn.example.com`.
  - <ins>Testing `httpserver`</ins>: Once an HTTP server is up and running, it can be tested using a simple `curl` statement. For example, if the HTTP server were running on my local machine on port 20090, the HTTP server could be tested via the command `curl http://127.0.0.1:20090/Main_Page`.
- <ins>Stopping the CDN</ins>: To run this script and stop the CDN, use the command `./stopCDN -p <port> -o <origin> -n <name> -u <username> -i <keyfile>`. Please see **Implementation Details** above for details on what exactly this script does. 

## Areas for Future Improvement

- [ ] Use Scamper to send both active and passive measurements from each HTTP server to the DNS server, so that the DNS server can refer clients to a more optimal HTTP server. For example, although a client might be geographically closer to an HTTP server in Los Angeles, CA, Scamper may demonstrate (via traceroute and pinging techniques) that the client would get faster service using the HTTP server in Boston, MA; or, for example, a client that is normally best served by an HTTP server in Tokyo may get faster service from an HTTP server in Mumbai, perhaps because the HTTP server in Tokyo is backed up with many requests while the HTTP server in Mumbai is idling.
- [ ] Rather than using the pre-determiend page rankings given in `pageviews.csv`, the rankings of pages could be re-computed to rank based off of views per byte of compressed data. This way, the cache hit ratio will be further optimized. 
- [ ] Currently, all 7 HTTP servers start to download the exact same pages of total size 7 MB at runtime to `/cache/` on disk storage (to complement the 13 MB of compressed origin server pages it is receiving from the DNS server). However, this places immense strain on the origin server; it may be faster to have each of the 7 HTTP servers download a different 1 MB segment from the other 6, and then have them `scp` these compressed files in the background.

## Program Demo (Video)

- To see this program in action, please see a demo video of this program [linked here](https://youtu.be/wZDAvp1cLME).

## Acknowledgements 

- Zhongwei Zhang, my partner for this project. 
- Professor Alden Jackson, my Computer Networking professor.

## Contact Information

- Alexander Wilcox
- Email: alexander.w.wilcox [at] gmail.com
