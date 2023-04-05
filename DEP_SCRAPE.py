# IMPORTS AND COMMON FUNCTIONS
import os, subprocess, sys, time, random, pathlib, csv, re, warnings, random
warnings.filterwarnings('ignore', category=DeprecationWarning)

try:
    import imp
    imp.find_module('selenium')
    imp.find_module('webdriver_manager')
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 
                           'install', 'selenium']);
    subprocess.check_call([sys.executable, '-m', 'pip', 
                           'install', 'webdriver_manager']);
    
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.chrome import ChromeDriverManager

working_directory = ''
if os.path.isfile(os.getcwd() + '\\FAST.txt'):
    working_directory = os.getcwd()
elif os.path.isfile(str(pathlib.Path.home() / 'Downloads\\FAST.txt')):
    working_directory = str(pathlib.Path.home() / 'Downloads')
else:
    print('FAST.txt file not found!\nPlace valid FAST.txt file in this ' \
          + 'folder or in your Downloads folder.\nDefault file:' \
          + ' https://raw.githubusercontent.com/glott/FAST/main/FAST.txt')

def read_config_value(key):
    config = open(working_directory + '\\FAST.txt', 'r').read()
    if key + '=' in config:
        return config.split(key + '=')[1].split('\n')[0]
    return 'NULL'

def between(text, start, end):
    try: 
        return text.split(start)[1].split(end)[0]
    except Exception:
        return ''
    
def click_button(text):
    try: 
        driver.find_element('xpath', 
            '//button[contains(text(), \'' + text + '\')]').click()
    except Exception:
        print('Unable to click button \'' + text + '\'.')
    
sleep_factor = float(read_config_value('SLOW_INTERNET_FACTOR'))

# OPEN BROWSER
print('-------------------- FAST --------------------')
browser = read_config_value('BROWSER').capitalize()
print('Opening ' + browser + '.')

driver = None
if 'C' in browser:
    options = webdriver.chrome.options.Options()
    options.add_argument('--ignore-certificate-errors')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    driver = webdriver.Chrome(executable_path=ChromeDriverManager()
        .install(), options=options);
else:
    driver = webdriver.Firefox(executable_path=GeckoDriverManager() \
        .install());
driver.minimize_window()

# GENERATE AIRCRAFT URLs
print('Logging in to FlightAware.')
url = 'https://flightaware.com/live/airport/' \
    + read_config_value('AIRPORT') + '/scheduled'

driver.get(url)

driver.find_element('name', 'flightaware_username') \
    .send_keys(read_config_value('FLIGHTAWARE_USER'))
driver.find_element('name', 'flightaware_password') \
    .send_keys(read_config_value('FLIGHTAWARE_PASS'))
driver.find_element('id', 'loginButton').click()
print('Successfully logged in to FlightAware.')

time.sleep(sleep_factor * 5)

plane_urls = driver.find_elements('xpath', '//a[@href]')
filtered_urls = list()
for plane_url in plane_urls:
    href = plane_url.get_attribute('href')
    if 'live/flight/id/' in href:
        filtered_urls.append(href)

# CREATE AIRCRAFT DATA FILE
s = 'ident,type,dep,arr,alt,speed,route,rules,equip,spawn-delay,' \
    + 'gate,push-taxiway,taxi-route'
init_spawn_delay = 0

print('Scraping departure data at ' + read_config_value('AIRPORT') + '.')

def get_plane_info(source):
    temp_text = source[source.rindex(r'"route"') - 3000:
                       source.rindex(r'"route"') + 1500]
    global init_spawn_delay

    ident = between(temp_text, r'"displayIdent":"', r'"')
    flight_plan = between(temp_text, r'"flightPlan":', r'"fuelBurn"')
    alt = between(flight_plan, r'"altitude":', r',') + '00'
    speed = between(flight_plan, r'"speed":', r',')
    route = between(flight_plan, r'"route":"', r'",').replace(',', '')
    delay = int(between(flight_plan, r'departure":', r',"ete"'))
    spawn_delay = 0 if init_spawn_delay == 0 else delay - init_spawn_delay
    dep = between(source, r'name="origin" content="', r'"')
    arr = between(source, r'name="destination" content="', r'"')
    acft = between(source, r'name="aircrafttype" content="', r'"')
    gate = 'UNKN' if not r'","gate":"' in source \
        else between(source, dep + r'","gate":"', r'"')

    alt = alt.replace('null0', '')
    if len(speed) == 0: speed = '0'
    if len(dep) == 0: dep = 'ZZZZ'
    if len(arr) == 0: arr = 'ZZZZ'
    if len(acft) == 0: acft = 'ZZZZ'
    if len(gate) == 0: gate = 'UNKN'
    
    if init_spawn_delay == 0: init_spawn_delay = delay

    return ','.join([ident, acft, dep, arr, alt, speed,
                     route, 'I', 'L', str(spawn_delay), gate, '', ''])

for filtered_url in filtered_urls:
    driver.get(filtered_url)
    plane = get_plane_info(driver.page_source)
    s += '\n' + plane
    print('Scraped ' + plane.split(',')[0] + '\t' \
        + plane.split(',')[2] + '-' + plane.split(',')[3] + ', ' \
        + plane.split(',')[1] + ', ' + plane.split(',')[4])
    time.sleep(sleep_factor * random.uniform(1, 5))

out_file = s.split('\n')[1].split(',')[2][1:] + '_DEP_IFR_' \
    + time.strftime('%y%m%d-%H%M', time.gmtime()) + '.csv'
print('Writing aircraft data to ' + str(out_file) + '.')
with open(working_directory + '\\' + out_file, 'w') as f: 
    f.write(s)

print('Departure scraping complete!')
driver.quit()