import json
import streamlit as st
import st_connection
import st_connection.snowflake
import pandas as pd
import pydeck as pdk
import numpy as np
import hydralit_components as hc


session = st.connection.snowflake_connection.singleton(st.secrets.snow)

st.markdown('''
<style>
.stApp header{
    display:none;
}
.stApp {
    background-attachment: fixed;
    background-size: cover
    }
.stApp {
    background-color:#f0f2f6;
}
.main .block-container{
    max-width: unset;
    padding-left: 15em;
    padding-right: 15em;
    padding-top: 1.5em;
    padding-bottom: 1em;
    }
</style>
''', unsafe_allow_html=True)
def getAllViews():
    queryAll=f'''
        SELECT count(distinct av_session_id) as ct
        FROM ATIDEMO.stream.events
        Where to_date(EVENT_TIME) BETWEEN '2022-11-01' AND to_date(CURRENT_DATE());
         '''
    df = pd.read_sql(queryAll, session)
    return df
def getPianoWeather():
    queryAll=f'''
        with broad as (
            SELECT distinct av_session_id,event_time,geo_city,geo_country,geo_latitude as lat,geo_longitude as lon, av_show
            FROM ATIDEMO.stream.events
            Where av_session_id is not null and event_name='av.play' 
                AND to_date(EVENT_TIME) BETWEEN '2022-11-01' AND to_date(CURRENT_DATE())
        )
        select * from broad
        LEFT JOIN 
            (SELECT    
                city_name,
                date_valid_std,
                ROUND((avg(AVG_TEMPERATURE_AIR_2M_F)-32)*5/9,2) as temp,
                case 
                    when avg(tot_precipitation_in) > 0.05 then 'rainy'
                    when avg(tot_precipitation_in) < 0.05 and avg(avg_cloud_cover_tot_pct) > 25 then 'cloudy'
                    else 'sunny'
                end as weather
            FROM 
                weather.onpoint_id.history_day 
            where  to_date(date_valid_std) BETWEEN '2022-11-01' AND to_date(CURRENT_DATE()) 
            group by city_name,date_valid_std 
            ) W
        on geo_city = W.city_name and to_date(EVENT_TIME)=to_date(date_valid_std)
        where city_name is not null;
    '''
    df = pd.read_sql(queryAll, session)
    return df

df=getPianoWeather()
df.rename(str.lower, axis='columns',inplace=True)
df.sort_values(by='geo_country', inplace=True)
df.sort_values(by='av_show', inplace=True)

st.markdown('## Today Live Views: ' + str(getAllViews().CT[0]))
   
countryUnique=list(df.geo_country.unique())
showunique=list(df.av_show.unique())
with st.expander("Filters"):
    country=st.multiselect("Countries",countryUnique,default=countryUnique)

    show=st.multiselect("TV Show",showunique,default=showunique)

    temp=st.slider("Filter by Temperature:",-10,40,(5, 15))
df.query(f'''av_show in {show}''',inplace=True)
df.query(f'''geo_country in {country}''',inplace=True)
# st.map(df[df.temp>temp[0]][df.temp<temp[1]]) 
df=df[df.temp>temp[0]][df.temp<temp[1]]


st.pydeck_chart(pdk.Deck(
    map_style='mapbox://styles/mapbox/light-v9',
    tooltip=True,
    initial_view_state=pdk.ViewState(
            latitude=48.85,
            longitude=-2.35,
            zoom=2.7,
            pitch=60,
            
        ),
    layers=[
        pdk.Layer(
           'HexagonLayer',
           data=df[['lon', 'lat']],
           get_position='[lon, lat]',
           radius=40000,
           coverage=1.6, 
           bearing=10,
           
           auto_highlight=True,
           elevation_scale=400,
           elevation_range=[0, 4000],
           pickable=True,
           extruded=True,
        ),
        # pdk.Layer(
        #     'ScatterplotLayer',     # Change the `type` positional argument here
        #     data=df[['lon', 'lat']],
        #     get_position=['lon', 'lat'],
        #     auto_highlight=True,
        #     get_radius=20000,          # Radius is given in meters
        #     get_fill_color=[180, 0, 200, 140],  # Set an RGBA value for fill
        #     pickable=True)
        ],
))
    
ds=df[df.weather == 'sunny']
dc=df[df.weather == 'cloudy']
dr=df[df.weather == 'rainy']
cloudy = {'icon': 'fa fa-cloud','icon_color':'darkgrey'}
sunny = {'icon': 'fa fa-sun','icon_color':'#FFCC00'}
rainy={'icon': 'fa fa-cloud-rain','icon_color':'grey'}
if(len(df)>0):
    st.markdown("## Views per Weather Conditions")
    col1,col2,col3=st.columns(3)
    snr=round((len(ds)/len(df))*100,2)
    cnr=round((len(dc)/len(df))*100,2)
    rnr=round((len(dr)/len(df))*100,2)
    icoSize="30vw"
    with col1:
        hc.info_card(key="2",title=str(snr)+'%', title_text_size="12vw",content="On Sunny Days",icon_size=icoSize,theme_override=sunny)
    with col2:
        hc.info_card(key="3",title=str(cnr)+'%',title_text_size="12vw",content="On Cloudy Days",icon_size=icoSize,theme_override=cloudy)   
    with col3:
        hc.info_card(key="4",title=str(rnr)+'%',title_text_size="12vw",content="On Rainy Days",icon_size=icoSize,theme_override=rainy)      