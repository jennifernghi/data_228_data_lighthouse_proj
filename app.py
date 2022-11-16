#app.py
import os
import pathlib
import requests
from flask import Flask, session, abort, redirect, request, render_template
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
from urllib.request import urlopen
import json
import plotly
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import date, datetime  
import numpy as np 
from keras.models import  load_model 
from sklearn.preprocessing import StandardScaler 

 

            
app = Flask(__name__)

app.secret_key = "a1239!sjhiiuwodji"  #it is necessary to set a password when dealing with OAuth 2.0

with urlopen('https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json') as response:
      counties = json.load(response)


@app.route("/")
def home():
    return render_template("index.html")


 
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  #this is to set our environment to https because OAuth 2.0 only supports https environments

GOOGLE_CLIENT_ID = "408540296694-akg8kc8fqob5eg2lkpb31f3pmbd1csil.apps.googleusercontent.com"  #enter your client id you got from Google console
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")  #set the path to where the .json file you got Google console is

flow = Flow.from_client_secrets_file(  #Flow is OAuth 2.0 a class that stores all the information on how we want to authorize our users
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],  #here we are specifing what do we get after the authorization
    redirect_uri="http://127.0.0.1:5000/callback"  #and the redirect URI is the point where the user will end up after the authorization
)



def login_is_required(function):  #a function to check if the user is authorized or not
    def wrapper(*args, **kwargs):
        if "google_id" not in session:  #authorization required
            return abort(401)
        else:
            return function()

    return wrapper


@app.route("/login")  #the page where the user can login
def login():
    authorization_url, state = flow.authorization_url()  #asking the flow class for the authorization (login) url
    session["state"] = state
    return redirect(authorization_url)


@app.route("/callback")  #this is the page that will handle the callback process meaning process after the authorization
def callback():
    flow.fetch_token(authorization_response=request.url)

    # if not session["state"] == request.args["state"]:
    #     abort(500)  #state does not match!

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )

    session["google_id"] = id_info.get("sub")  #defing the results to show on the page
    session["name"] = id_info.get("name")
    session["picture"] = id_info.get("picture")
  
    return redirect("/protected_area")  #the final page where the authorized users will end up


@app.route("/logout")  #the logout page and function
def logout():
    session.clear()
    return redirect("/")


# @app.route("/")  #the home page where the login button will be located
# def index():
#     return "Hello World <a href='/login'><button>Login</button></a>"


@app.route("/protected_area")  #the page where only the authorized users can go to
@login_is_required
def protected_area():
    return render_template('dashboard.html', session=session,  )
    # return f"Hello {session['name']}! <br/> <a href='/logout'><button>Logout</button></a>"  #the logout button 



def yield_choloplete_map():
    with urlopen('https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json') as response:
        counties = json.load(response)
    df = pd.read_csv("https://raw.githubusercontent.com/plotly/datasets/master/fips-unemp-16.csv", dtype={"fips": str})
    fig = px.choropleth(df, geojson=counties, locations='fips', color='unemp',
                           color_continuous_scale="Viridis",
                           range_color=(0, 12),
                           scope="usa",
                           labels={'unemp':'p'}
                          )
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return graphJSON


@app.route('/analyze_callback', methods=['POST', 'GET'])
def cb(): 

    lst = [
    get_doy(request.args.get('date_select')), get_time(request.args.get('time_select')),
    request.args.get('cause_dd'), request.args.get('CAUSE_AGE_CATEGORY'), request.args.get('general_cause'), 
    request.args.get('burning_index'), request.args.get('min_air_temperature_K_avg'),  request.args.get('max_air_temperature_K_avg'),
    request.args.get('max_relative_humidity_avg'), request.args.get('min_relative_humidity_avg'),  request.args.get('precipitation_amount_avg'),
    request.args.get('specific_humidity'), request.args.get('surface_downwelling_shortwave_flux_avg'),  request.args.get('wind_speed_avg'),]

    
    
    fips_mapping = pd.read_csv('saved_model/fips_reference.csv') 
    fips_mapping = fips_mapping.loc[:, ~fips_mapping.columns.str.contains('^Unnamed')]

 
    model = load_model("saved_model/DNN_v5.h5")
    scaler=StandardScaler()
    
    x = scaler.fit_transform(np.array(lst,  dtype=np.float).reshape((1, 14))) ## data inputs here
    pred = model.predict(x)[0]

    df = fips_mapping[['items']].rename(columns={"items": "FIPS" })
    df['state_code'] = 6
    df['FIPS'] = df.FIPS.astype(int)
    df['FIPS'] = df.FIPS.astype(str)
    df['FIPS'] = df.FIPS.str.zfill(5)
    
    df['p'] =pred 
    county_df = pd.read_csv("saved_model/county_codes.csv")
    
    county_df = county_df[county_df['State_ANSI'] == 6]
    county_df.rename(columns={"Geo Code": "FIPS", "State_ANSI": "state_code" }, inplace=True)
    county_df['FIPS'] = county_df.FIPS.astype(int)
    county_df['FIPS'] = county_df.FIPS.astype(str)
    county_df['FIPS'] = county_df.FIPS.str.zfill(5)
 
    
    df = pd.merge(df, county_df, on=['state_code', 'FIPS']) 
 
    fig = px.choropleth(df, geojson=counties, locations='FIPS', color='p',
                          color_continuous_scale="Viridis",
                          range_color=(df['p'].min(), df['p'].max()),
                          scope="usa", 
                          labels={'pred': 'p'}
                          )
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
      
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return graphJSON



@app.route('/analyze_callback2', methods=['POST', 'GET'])
def cb2(): 

    lst = [
    get_doy(request.args.get('date_select')), get_time(request.args.get('time_select')),
    request.args.get('cause_dd'), request.args.get('CAUSE_AGE_CATEGORY'), request.args.get('general_cause'), 
    request.args.get('burning_index'), request.args.get('min_air_temperature_K_avg'),  request.args.get('max_air_temperature_K_avg'),
    request.args.get('max_relative_humidity_avg'), request.args.get('min_relative_humidity_avg'),  request.args.get('precipitation_amount_avg'),
    request.args.get('specific_humidity'), request.args.get('surface_downwelling_shortwave_flux_avg'),  request.args.get('wind_speed_avg'),]
   
    fips_mapping = pd.read_csv('saved_model/fips_reference.csv') 
    fips_mapping = fips_mapping.loc[:, ~fips_mapping.columns.str.contains('^Unnamed')]

 
    model = load_model("saved_model/DNN_v5.h5")
    scaler=StandardScaler()
    
    x = scaler.fit_transform(np.array(lst,  dtype=np.float).reshape((1, 14))) ## data inputs here
    pred = model.predict(x)[0]

    df = fips_mapping[['items']].rename(columns={"items": "FIPS" })
    df['state_code'] = 6
    df['FIPS'] = df.FIPS.astype(int)
    df['FIPS'] = df.FIPS.astype(str)
    df['FIPS'] = df.FIPS.str.zfill(5)
    
    df['p'] =pred

    df = df.sort_values(by=['p'], ascending=False)

    county_df = pd.read_csv("saved_model/county_codes.csv")
    
    county_df = county_df[county_df['State_ANSI'] == 6]
    county_df.rename(columns={"Geo Code": "FIPS", "State_ANSI": "state_code" }, inplace=True)
    county_df['FIPS'] = county_df.FIPS.astype(int)
    county_df['FIPS'] = county_df.FIPS.astype(str)
    county_df['FIPS'] = county_df.FIPS.str.zfill(5)
 
    
    df = pd.merge(df, county_df, on=['state_code', 'FIPS']) 
 
 
    fig = px.bar(df, y='p', x='County Name', text='p')
    fig.update_traces(texttemplate='%{text:.2s}', textposition='outside')
    fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')

    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON


 
def get_doy(d):
    d = d.split("/")
    year = int(d[2])
    month = int(d[0])
    day = int(d[1]) 
    date_val = date(year, month, day)
 
    day_of_year = date_val.strftime('%j')
    return int(day_of_year)

def get_time(t):
    in_time = datetime.strptime(t, "%I:%M %p")
    out_time = datetime.strftime(in_time, "%H:%M")
    return float(out_time.replace(":",""))

if __name__ == "__main__":
    app.run(debug=True)