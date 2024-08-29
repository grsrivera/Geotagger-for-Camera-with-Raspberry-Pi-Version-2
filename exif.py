from datetime import datetime, timedelta
import pickle
import os
import piexif

def make_photo_file_path_list():
# Make list of all photo filenames
    folder_path = 'C:/Users/geral/Documents/GitHub/Geotagger V2/Photos/'

    # Make list of all photo files in folder
    filename_list = os.listdir(folder_path)
    
    photo_file_path_list = []

    for file in filename_list:
        file_path = folder_path + file
        photo_file_path_list.append(file_path)

    return photo_file_path_list

def find_photo_datetime(file_path, timezone_shift, sync_time):
    metadata = piexif.load(file_path)
    photo_datetime_str = metadata['0th'][306].decode()
    photo_datetime_object = datetime.strptime(photo_datetime_str, '%Y:%m:%d %H:%M:%S')

    sync_time = datetime.strptime(sync_time, '%Y:%m:%d %H:%M:%S')
    time_elapsed = (photo_datetime_object - sync_time).total_seconds()/3600 # Units: hrs


    delta_time = -0.0000154*time_elapsed + 0.0001249
    ## print(f'delta time: {delta_time} and in sec {delta_time*3600}') ## delta_time*3600 will show wrong on its own, but with photo time in the next line it will be okay
    corrected_photo_datetime_object = photo_datetime_object + timedelta(hours=timezone_shift + delta_time)
    # corrected_photo_datetime_object = photo_datetime_object + timedelta(hours=timezone_shift)
    if corrected_photo_datetime_object.microsecond >= 500_000:
        corrected_photo_datetime_object = corrected_photo_datetime_object + timedelta(seconds=1)
    corrected_photo_datetime_object = corrected_photo_datetime_object.replace(microsecond=0)
    
    print(f'Original: {photo_datetime_object}')
    print(f'Corrected: {corrected_photo_datetime_object}')

    corrected_photo_datetime_str = corrected_photo_datetime_object.strftime('%Y:%m:%d %H:%M:%S')
    corrected_photo_date, corrected_photo_time = corrected_photo_datetime_str.split(' ')
    corrected_photo_date = corrected_photo_date.split(':')
    corrected_photo_date = corrected_photo_date[0] + '_' + corrected_photo_date[1] + '_' + corrected_photo_date[2]

    return corrected_photo_date, corrected_photo_time

def find_geotag(photo_date, photo_time, file_path, i):
    photo_file = file_path.replace('C:/Users/geral/Documents/GitHub/Geotagger V2/Photos/', '')
    # pkl_file = file_path.replace('C:/Users/geral/Documents/GitHub/Geotagger V2/list_files/', '')

    def make_pkl_file_list():
        folder_path = 'C:/Users/geral/Documents/GitHub/Geotagger V2/list_files/'

        # Make list of all pkl files in folder
        pkl_file_list = os.listdir(folder_path)
        return pkl_file_list
    
    def get_geotag():
        with open(f'C:/Users/geral/Documents/GitHub/Geotagger V2/list_files/{photo_date}.pkl', 'rb') as file:
            geotag_list = pickle.load(file)

        geotag_times_list = []

        for geotag in geotag_list:
            data = geotag.split(',')
            
            if data[1]:
                geotag_time = data[1][0:2] + ':' + data[1][2:4] + ':' + data[1][4:6]
            else: 
                geotag_time = 'No time'

            geotag_times_list.append(geotag_time)
        
        if photo_time in geotag_times_list:
            photo_index = geotag_times_list.index(photo_time)
            for geotag_time in geotag_times_list:
                if geotag_time == photo_time and geotag_list[photo_index].split(',')[2] == '':
                    return f'{i}. {photo_file}: Geotag was negative-fix for photo'
                elif geotag_time == photo_time and geotag_list[photo_index].split(',')[2] != '':
                    geotag_index = geotag_times_list.index(geotag_time)
                    print(f'{i}. {photo_file}: Good geotag. Adding EXIF.')
                    return geotag_list[geotag_index]
        else:
            return f'{i}. {photo_file}: No geotags associated with photo in pkl file'
            
            
    pkl_file_list = make_pkl_file_list()

    if f'{photo_date}.pkl' not in pkl_file_list:
        return f'{i}. {photo_file}: No pkl file associated with photo'
    else:
        return get_geotag()
    
def convert_geotag(raw_data):
# Does the DDM to DMS (for lat/long) to EXIF conversion
# Also formats elevation to EXIF
# Sample from GPS: [$GPGGA,185157.00,3730.95031,N,12217.97738,W,1,05,1.77,120.7,M,-30.0,M,,*63]
# Sample DDS: ['18:51:57', 37, 30, 57.019, 'N', 1202 17, 58.643, 'W', '120.7']
    data = raw_data.split(',')

    # DDM to DDS for lat/long
    if data[2]: # Only check for lat because cannot have lat w/o long and vice versa
        # For lat first
        lat_hemi = data[3]
        lat_deg = int(data[2][0:2])
        lat_min = int(data[2][2:4])
        lat_sec = round(float(data[2][4:10])*60*1000)   # *1000 to divide by 1000 in EXIF

        # Then longitude next
        long_hemi = data[5]
        long_deg = int(data[4][0:3])
        long_min = int(data[4][3:5])
        long_sec = round(float(data[4][5:11])*60*1000)
        
        # Then DDS to EXIF for lat/long
        lat_EXIF = [lat_hemi, ((lat_deg,1), (lat_min,1), (lat_sec,1000))]
        long_EXIF = [long_hemi, ((long_deg,1), (long_min,1), (long_sec,1000))]
    else:
        lat_EXIF = 'No latitude'
        long_EXIF = 'No longitude'
    
    # Elevation to EXIF
    if data[9]:
        elev_EXIF = (round(float(data[9])*10),10) # Multiply by 10 to divide by 10 in EXIF format 
    else:
        elev_EXIF = 'No elevation'
    
    converted_geotag = [lat_EXIF, long_EXIF, elev_EXIF]

    return converted_geotag

def tag_photo(file_path, converted_geotag):
    metadata = piexif.load(file_path)
    metadata['GPS'][1] = converted_geotag[0][0]
    metadata['GPS'][2] = converted_geotag[0][1]
    metadata['GPS'][3] = converted_geotag[1][0]
    metadata['GPS'][4] = converted_geotag[1][1]
    metadata['GPS'][6] = converted_geotag[2]

    EXIF_bytes = piexif.dump(metadata)
    piexif.insert(EXIF_bytes, file_path)

print()

photo_file_path_list = make_photo_file_path_list()
timezone_shift = int(input("Hours from you to GMT? "))
sync_time = str(input('Time you synced camera in YYYY:MM:DD HH:MM:SS (24hr time)'))

print()

i = 1
for file_path in photo_file_path_list:
    photo_date, photo_time = find_photo_datetime(file_path, timezone_shift, sync_time)
    geotag = find_geotag(photo_date, photo_time, file_path, i)
    
    if '$GPGGA' in geotag:
        converted_geotag = convert_geotag(geotag)
        tag_photo(file_path, converted_geotag)
    else:
        print(geotag, end='\n')
    i = i + 1

