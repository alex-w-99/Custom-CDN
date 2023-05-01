from bisect import bisect_left

class GeoInfo:

    def __init__(self, ip_csv, coordinates_csv):
        self.ip_ranges = list()
        self.country_codes = list()
        self.country_coordinates = dict()
        with open(ip_csv, "r") as f1:
            for line in f1:
                start, end, country_code = line.strip().split(',')
                start, end = int(start), int(end)
                self.ip_ranges.append((start, end))
                self.country_codes.append(country_code)
        with open(coordinates_csv, "r") as f2:
            f2.readline() 
            for line in f2:
                country_code, latitude, longitude = line.strip().split(',')
                if latitude and longitude:  # Check if latitude and longitude values are not empty strings
                    try:
                        self.country_coordinates[country_code] = (float(latitude), float(longitude))
                    except ValueError:
                        pass
                
    def find_country_code(self, ip_address):
        """
        Find the country code based on given ip address.
        """
        ip_decimal = self.ip_to_decimal(ip_address)
        index = bisect_left(self.ip_ranges, (ip_decimal,)) - 1
        if index >= 0 and self.ip_ranges[index][0] <= ip_decimal <= self.ip_ranges[index][1]:
            return self.country_codes[index]
        return None

    def get_coordinates_geo_center(self, ip_address):
        """
        Use the ip address and find the country code, with which to find the coordinates.
        """
        country_code = self.find_country_code(ip_address)
        if country_code in self.country_coordinates:
            return self.country_coordinates[country_code]
        else:
            return None

    @staticmethod
    def ip_to_decimal(ip_address):
        """
        Transform ip address string to decimal format.
        """
        ip_parts = [int(part) for part in ip_address.split('.')]
        return (ip_parts[0] << 24) + (ip_parts[1] << 16) + (ip_parts[2] << 8) + ip_parts[3]

