# Utah-stats Project Guide

This project collects and analyzes statistical data about Utah using official US government APIs. This document describes how to pull data from the US Census Bureau, Bureau of Labor Statistics, Bureau of Economic Analysis, FRED, and Utah-specific sources.

## API Key Management

Store all API keys in environment variables. Never commit keys to the repository.

```bash
export CENSUS_API_KEY="your_key_here"
export BLS_API_KEY="your_key_here"
export BEA_API_KEY="your_key_here"
export FRED_API_KEY="your_key_here"
```

| API | Registration URL | Cost |
|-----|-----------------|------|
| Census Bureau | https://api.census.gov/data/key_signup.html | Free |
| BLS | https://www.bls.gov/developers/home.htm | Free |
| BEA | https://apps.bea.gov/api/signup/ | Free |
| FRED | https://fred.stlouisfed.org/docs/api/api_key.html | Free |

## Utah FIPS Codes

Utah's state FIPS code is **49**. Use this in all geographic queries.

### County FIPS Codes

| FIPS | County | FIPS | County |
|------|--------|------|--------|
| 49001 | Beaver | 49029 | Morgan |
| 49003 | Box Elder | 49031 | Piute |
| 49005 | Cache | 49033 | Rich |
| 49007 | Carbon | 49035 | **Salt Lake** |
| 49009 | Daggett | 49037 | San Juan |
| 49011 | **Davis** | 49039 | Sanpete |
| 49013 | Duchesne | 49041 | Sevier |
| 49015 | Emery | 49043 | Summit |
| 49017 | Garfield | 49045 | Tooele |
| 49019 | Grand | 49047 | Uintah |
| 49021 | Iron | 49049 | **Utah** |
| 49023 | Juab | 49051 | Wasatch |
| 49025 | Kane | 49053 | Washington |
| 49027 | Millard | 49055 | Wayne |
| | | 49057 | **Weber** |

The four Wasatch Front counties (Salt Lake, Utah, Davis, Weber) contain roughly 75% of Utah's population.

---

## 1. US Census Bureau API

**Base URL:** `https://api.census.gov/data/`
**Documentation:** https://www.census.gov/data/developers/guidance/api-user-guide.html
**Dataset discovery:** https://api.census.gov/data.html

### Query Structure

```
https://api.census.gov/data/{year}/{dataset}?get={variables}&for={geography}&key={your_key}
```

### Major Datasets

| Dataset | API Path | Description |
|---------|----------|-------------|
| ACS 5-Year | `/data/{year}/acs/acs5` | Pooled 5-year estimates, available down to block group level |
| ACS 1-Year | `/data/{year}/acs/acs1` | Annual estimates for areas with population 65,000+ |
| Decennial Census 2020 | `/data/2020/dec/dhc` | Full-count Demographic and Housing Characteristics |
| Decennial Census 2010 | `/data/2010/dec/sf1` | Summary File 1 |
| Population Estimates | `/data/{vintage}/pep/population` | Annual intercensal population estimates |
| SAIPE | `/data/timeseries/poverty/saipe/schdist` | Small Area Income and Poverty Estimates |

### Common ACS Variables

Find all variables for a dataset at:
`https://api.census.gov/data/{year}/{dataset}/variables.html`

| Variable | Description |
|----------|-------------|
| `NAME` | Geographic area name (always include this) |
| `B01003_001E` | Total population |
| `B19013_001E` | Median household income |
| `B17001_001E` | Poverty status -- total universe |
| `B17001_002E` | Income below poverty level |
| `B19301_001E` | Per capita income |
| `B01001_001E` | Sex by age -- total |

Variable naming convention: `B{table}_{line}{suffix}` where `E` = estimate, `M` = margin of error.

### Geography Syntax

| Geography Level | Syntax |
|----------------|--------|
| All states | `&for=state:*` |
| Utah | `&for=state:49` |
| All counties in Utah | `&for=county:*&in=state:49` |
| Salt Lake County | `&for=county:035&in=state:49` |
| All tracts in a county | `&for=tract:*&in=state:49&in=county:035` |
| All block groups | `&for=block%20group:*&in=state:49&in=county:035&in=tract:*` |
| Congressional districts | `&for=congressional%20district:*&in=state:49` |
| ZIP Code Tabulation Areas | `&for=zip%20code%20tabulation%20area:*` |

Multiple geographies in one call using `ucgid`:
```
&ucgid=0400000US49,0500000US49035
```

### Example Calls

**All Utah counties -- population and median income (ACS 5-Year):**
```
https://api.census.gov/data/2023/acs/acs5?get=NAME,B01003_001E,B19013_001E&for=county:*&in=state:49&key=YOUR_KEY
```

**Salt Lake County census tracts -- population and poverty:**
```
https://api.census.gov/data/2023/acs/acs5?get=NAME,B01003_001E,B17001_002E&for=tract:*&in=state:49&in=county:035&key=YOUR_KEY
```

**2020 Decennial Census -- Utah county populations:**
```
https://api.census.gov/data/2020/dec/dhc?get=NAME,P1_001N&for=county:*&in=state:49&key=YOUR_KEY
```

### Rate Limits

- Without API key: 500 queries per IP per day, up to 50 variables per query
- With API key: higher limits, subject to api.data.gov rate limiting
- Exceeding limits results in a temporary block (~1 hour)
- Response format: JSON by default

### Python Example

```python
import requests

API_KEY = os.environ["CENSUS_API_KEY"]
base_url = "https://api.census.gov/data/2023/acs/acs5"

params = {
    "get": "NAME,B01003_001E,B19013_001E",
    "for": "county:*",
    "in": "state:49",
    "key": API_KEY,
}

response = requests.get(base_url, params=params)
data = response.json()
# First row is header, remaining rows are data
header = data[0]
rows = data[1:]
```

---

## 2. Bureau of Labor Statistics (BLS) API

**Endpoint:** `https://api.bls.gov/publicAPI/v2/timeseries/data/`
**Documentation:** https://www.bls.gov/developers/home.htm

### API Versions

| Feature | v1 (No Key) | v2 (With Key) |
|---------|-------------|---------------|
| Daily query limit | 25 | 500 |
| Years per query | 10 | 20 |
| Series per query | 25 | 50 |
| Annual averages | No | Yes |

### Useful Series IDs

| Series ID | Description |
|-----------|-------------|
| `CUUR0000SA0` | CPI-U, All items, US city average |
| `LNS14000000` | Unemployment rate (seasonally adjusted) |
| `PAYEMS` / `CES0000000001` | Total nonfarm employment |
| `LAUCN494900000000003` | Utah unemployment rate (local area) |

Dataset categories: CPI, Employment & Wages (QCEW), Local Area Unemployment (LAUS), Current Employment Statistics (CES), Occupational Employment & Wage Statistics (OEWS), JOLTS, PPI, Productivity & Costs.

### Example Call (POST, v2)

```python
import requests
import json

url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
headers = {"Content-type": "application/json"}
payload = json.dumps({
    "seriesid": ["CUUR0000SA0", "LNS14000000"],
    "startyear": "2020",
    "endyear": "2025",
    "registrationkey": os.environ["BLS_API_KEY"],
})

response = requests.post(url, data=payload, headers=headers)
result = response.json()

for series in result["Results"]["series"]:
    for item in series["data"]:
        print(f"{item['year']}-{item['period']}: {item['value']}")
```

**Simple GET (v1, no key):**
```
https://api.bls.gov/publicAPI/v1/timeseries/data/CUUR0000SA0
```

---

## 3. Bureau of Economic Analysis (BEA) API

**Endpoint:** `https://apps.bea.gov/api/data`
**Documentation:** https://apps.bea.gov/API/docs/index.htm

Every request requires `UserID` (API key) and `method` parameters.

### Methods

| Method | Purpose |
|--------|---------|
| `GetDataSetList` | List all available datasets |
| `GetParameterList` | List parameters for a dataset |
| `GetParameterValues` | List valid values for a parameter |
| `GetData` | Retrieve data |

### Key Datasets

| Dataset | Description |
|---------|-------------|
| `NIPA` | National Income and Product Accounts (GDP, consumption, investment) |
| `GDPbyIndustry` | GDP broken down by industry |
| `Regional` | State/county personal income, GDP, employment |

### Key Regional Tables

| Table | Description |
|-------|-------------|
| `CAGDP9` | Real GDP by county/metro area |
| `CAINC1` | County/MSA personal income summary |
| `CAINC4` | Personal income summary |
| `SASUMMARY` | State annual summary |

### Example Calls

**Utah personal income:**
```
https://apps.bea.gov/api/data?&UserID=YOUR_KEY&method=GetData&DataSetName=Regional&TableName=CAINC4&LineCode=1&GeoFIPS=49000&Year=2023&ResultFormat=JSON
```

**National GDP (quarterly):**
```
https://apps.bea.gov/api/data?&UserID=YOUR_KEY&method=GetData&DataSetName=NIPA&TableName=T10101&Frequency=Q&Year=ALL&ResultFormat=JSON
```

**Per capita personal income for Utah:**
```
https://apps.bea.gov/api/data?&UserID=YOUR_KEY&method=GetData&DataSetName=Regional&TableName=CAINC5&LineCode=1&GeoFIPS=49000&Year=2020,2021,2022,2023&ResultFormat=JSON
```

### Rate Limits

100 requests/minute, 100 MB/minute, 30 errors/minute.

---

## 4. FRED (Federal Reserve Economic Data)

**Base URL:** `https://api.stlouisfed.org/fred/`
**Documentation:** https://fred.stlouisfed.org/docs/api/fred/

### Key Endpoints

| Endpoint | Purpose |
|----------|---------|
| `fred/series/observations` | Get data values for a series |
| `fred/series/search` | Search for series by text |
| `fred/series` | Get metadata about a series |
| `fred/category/series` | Get series in a category |

### Key Series IDs

**GDP and Output:**
`GDP` (nominal quarterly), `GDPC1` (real quarterly), `INDPRO` (industrial production)

**Labor Market:**
`UNRATE` (unemployment rate), `PAYEMS` (nonfarm payrolls), `CIVPART` (labor force participation), `ICSA` (initial jobless claims)

**Inflation:**
`CPIAUCSL` (CPI, seasonally adjusted), `CPILFESL` (core CPI), `PCEPI` (PCE price index)

**Interest Rates:**
`FEDFUNDS` (fed funds rate), `DGS10` (10-year Treasury), `MORTGAGE30US` (30-year mortgage)

**Utah-Specific:**
`UTUR` (Utah unemployment rate), `UTNGSP` (Utah gross state product)

### Example Calls

**Utah unemployment rate:**
```
https://api.stlouisfed.org/fred/series/observations?series_id=UTUR&api_key=YOUR_KEY&file_type=json
```

**Search for Utah series:**
```
https://api.stlouisfed.org/fred/series/search?search_text=utah&api_key=YOUR_KEY&file_type=json
```

**GDP with date range:**
```
https://api.stlouisfed.org/fred/series/observations?series_id=GDP&api_key=YOUR_KEY&file_type=json&observation_start=2020-01-01&observation_end=2025-12-31
```

### Frequency Aggregation

`d` (daily), `w` (weekly), `m` (monthly), `q` (quarterly), `sa` (semiannual), `a` (annual)

### Output Formats

`file_type=json`, `xml` (default), `xlsx`, `csv` (zipped)

### Python Library

```python
from fredapi import Fred

fred = Fred(api_key=os.environ["FRED_API_KEY"])
utah_unemployment = fred.get_series("UTUR")
results = fred.search("Utah unemployment")
```

Install: `pip install fredapi`

---

## 5. Utah-Specific Data Sources

| Source | URL | Description |
|--------|-----|-------------|
| Utah Open Data Portal | https://opendata.utah.gov/ | State datasets via Socrata/SODA API |
| Utah GIS (SGID) | https://opendata.gis.utah.gov/ | State Geographic Information Database |
| Utah IBIS | https://ibis.utah.gov/ | Public health indicator data |
| Utah DWS | https://jobs.utah.gov/wi/ | Labor market information |
| UDOT Open Data | https://data-uplan.opendata.arcgis.com/ | Transportation geospatial data |

### Utah Open Data Portal (Socrata/SODA API)

Each dataset on https://opendata.utah.gov/ has a SODA API endpoint:
```
https://opendata.utah.gov/resource/{dataset-id}.json
```

No API key is required for browsing and downloading. The SODA API supports filtering, sorting, and pagination via query parameters. See https://dev.socrata.com/consumers/getting-started.html for SODA API documentation.

---

## 6. Other Federal Data Portals

| Portal | URL | Description |
|--------|-----|-------------|
| data.gov | https://catalog.data.gov/dataset/ | 370,000+ federal datasets |
| HealthData.gov | https://healthdata.gov/ | Health and human services |
| USAspending.gov | https://usaspending.gov/ | Federal spending (has API) |
| EPA Data | https://www.epa.gov/data | Environmental data |
| USDA ERS | https://www.ers.usda.gov/data-products/ | Agricultural economics |
| HUD User | https://www.huduser.gov/portal/datasets/ | Housing data |

Search data.gov programmatically via its CKAN API:
```
https://catalog.data.gov/api/3/action/package_search?q=utah+population
```

---

## General Guidelines for Working with Government APIs

1. **Always use environment variables for API keys** -- never hardcode them.
2. **Respect rate limits** -- add delays between requests when making bulk queries. Use exponential backoff on errors.
3. **Cache responses locally** -- government data changes infrequently (often annually). Store responses to avoid redundant API calls.
4. **Check data vintages** -- Census ACS data lags by 1-2 years. The "2023 ACS 5-Year" covers 2019-2023. Decennial Census data is released on a rolling schedule after Census Day.
5. **Handle margins of error** -- ACS estimates include margins of error (suffix `M`). Always fetch and report these alongside estimates for statistical rigor.
6. **Verify FIPS codes** -- geographic identifiers change over time. Confirm codes against the Census FIPS lookup at https://geocoding.geo.census.gov/.
7. **Use JSON format** -- all these APIs support JSON responses. Prefer JSON over XML for easier parsing.
8. **Check for API changes** -- government APIs occasionally restructure endpoints or retire datasets. Consult the official documentation links above if calls begin failing.
