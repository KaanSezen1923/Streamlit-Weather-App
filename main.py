import streamlit as st
import requests
import os
from datetime import datetime  
import google.generativeai as genai
import matplotlib.pyplot as plt 
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import speech_recognition as sr 

st.set_page_config(page_title="MeteoMind",page_icon="icon.png")

with st.sidebar:
    gemini_api_key=st.text_input("Enter Gemini Api Key")
    weather_api_key=st.text_input("Enter OpenWeather Api Key")

def recognize_speech():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Konuşmaya başlayabilirsiniz...")
        try:
            audio = recognizer.listen(source, timeout=5)
            text = recognizer.recognize_google(audio, language="tr-TR")
            st.success(f"Saptanan metin: {text}")
            return text
        except sr.UnknownValueError:
            st.error("Ses anlaşılamadı, lütfen tekrar deneyin.")
        except sr.RequestError as e:
            st.error(f"Ses tanıma servisiyle ilgili bir sorun oluştu: {e}")
        return None
    
    
def play_response_text(response_text, lang="tr"):
    tts = gTTS(text=response_text, lang=lang)
    tts.save("response.mp3")
    with open("response.mp3", "rb") as audio_file:
        audio_bytes = audio_file.read()
        st.audio(audio_bytes, format="audio/mp3")
    os.remove("response.mp3")

def gemini_configeration(gemini_api_key):

    
    genai.configure(api_key=gemini_api_key)

    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }

    
    model = genai.GenerativeModel(
        model_name="gemini-1.5-pro",
        generation_config=generation_config,
    )

    chat_session = model.start_chat(history=[])
    
    return chat_session


def get_weather_data(city, weather_api_key):
    base_url = "http://api.openweathermap.org/data/2.5/weather?"
    complete_url = f"{base_url}appid={weather_api_key}&q={city}"
    response = requests.get(complete_url)
    return response.json()

def get_weather_icon_url(icon_code):
    base_url = "http://openweathermap.org/img/wn/"
    return f"{base_url}{icon_code}@2x.png"


def generate_weather_description_with_icon(data):
    try:
        temperature = data["main"]["temp"] - 273.15
        description = data["weather"][0]["description"]
        icon_code = data["weather"][0]["icon"]
        icon_url = get_weather_icon_url(icon_code)
        
        prompt = (
            f"Şu an şehrinizdeki hava durumu {description} "
            f"ve sıcaklık {temperature:.1f}°C. Bu hava koşulunu basit bir şekilde açıklayın. "
            f"Ayrıca, bu hava koşuluna uygun bir etkinlik önerisi yapın. "
            f"Eğer şiddetli bir hava durumu varsa (örneğin, fırtına, yoğun yağış, aşırı sıcaklık), kullanıcılara bu duruma karşı bir uyarıda bulunun."
        )

        chat_session = gemini_configeration(gemini_api_key)
        response = chat_session.send_message(prompt)

        return response.text, icon_url
    except Exception as e:
        return f"Error generating description: {e}", None


def get_weekly_forecast(weather_api_key, lat, lon):
    base_url = "https://api.openweathermap.org/data/2.5/"
    complete_url = f"{base_url}forecast?lat={lat}&lon={lon}&appid={weather_api_key}"
    response = requests.get(complete_url)
    return response.json()


def display_weekly_forecast(data,icon_url):
    try:
        st.write("### Weekly Weather Forecast")
        displayed_dates = set()
        
        header_cols = st.columns([1, 3, 3, 2, 2])
        with header_cols[0]:
            st.write("**Icon**")
        with header_cols[1]:
            st.write("**Date**")
        with header_cols[2]:
            st.write("**Description**")
        with header_cols[3]:
            st.write("**Min Temp**")
        with header_cols[4]:
            st.write("**Max Temp**")

        for day in data['list']:
            date = datetime.fromtimestamp(day['dt']).strftime('%A, %B %d')  
            
            if date not in displayed_dates:
                displayed_dates.add(date)

                min_temp = day['main']['temp_min'] - 273.15  
                max_temp = day['main']['temp_max'] - 273.15  
                description = day['weather'][0]['description']
                icon_code = day['weather'][0]['icon']
                icon_url = get_weather_icon_url(icon_code)

                
                cols = st.columns([1, 2, 2, 2, 2])  
                with cols[0]:
                    
                    st.image(icon_url, width=50)  
                with cols[1]:
                 
                    st.write(date)
                with cols[2]:
                   
                    st.write(description.capitalize())
                with cols[3]:
                   
                    st.write(f"{min_temp:.1f}°C")
                with cols[4]:
                  
                    st.write(f"{max_temp:.1f}°C")
    except Exception as e:
        st.error(f"Error displaying the weekly forecast: {str(e)}") 
        
def plot_temperature_graph(data):

    try:
        
        dates = []
        min_temps = []
        max_temps = []

        for day in data['list']:
            date = datetime.fromtimestamp(day['dt']).strftime('%A, %B %d')

            if date not in dates:
                dates.append(date)
                min_temps.append(day['main']['temp_min'] - 273.15)  
                max_temps.append(day['main']['temp_max'] - 273.15)  

        
        plt.figure(figsize=(10, 6))
        plt.plot(dates, min_temps, marker='o', label='Min Temp (°C)', color='blue')
        plt.plot(dates, max_temps, marker='o', label='Max Temp (°C)', color='red')
        plt.fill_between(dates, min_temps, max_temps, color='lightgray', alpha=0.3)
        
       
        plt.xticks(rotation=45, ha='right')
        plt.xlabel('Date')
        plt.ylabel('Temperature (°C)')
        plt.title('Weekly Temperature Forecast')
        plt.legend()
        plt.tight_layout()

       
        st.pyplot(plt)
    except Exception as e:
        st.error(f"Error plotting the temperature graph: {e}")
        
def all_process(city,weather_api_key,choice="text"):
    st.title(f"Weather Updates for {city}")
    with st.spinner("Fetching weather data..."):
        weather_data = get_weather_data(city, weather_api_key)

    if weather_data.get("cod") != "404":
        col1, col2 = st.columns(2)

        with col1:
            st.metric("Temperature 🌡️", f"{weather_data['main']['temp'] - 273.15:.2f} °C")
            st.metric("Humidity 💧", f"{weather_data['main']['humidity']}%")

        with col2:
            st.metric("Pressure", f"{weather_data['main']['pressure']} hPa")
            st.metric("Wind Speed 🍃", f"{weather_data['wind']['speed']} m/s")

        lat = weather_data["coord"]["lat"]
        lon = weather_data["coord"]["lon"]

        weather_description,icon_url = generate_weather_description_with_icon(weather_data)
        st.subheader("Weather Description")
        if choice == "audio":
            st.write(weather_description)
            play_response_text(weather_description)
        else:
            st.write(weather_description)
        
        st.subheader("City Location on Map")
        map_data = {
            "lat": [lat],
            "lon": [lon],
        }
        st.map(map_data)

        forecast_data = get_weekly_forecast(weather_api_key, lat, lon)
        if forecast_data.get("cod") != "404":
            display_weekly_forecast(forecast_data,icon_url)
            st.subheader("Temperature Graph")
            plot_temperature_graph(forecast_data)
        else:
            st.error("Error fetching weekly forecast data!")
    else:
        st.error(f"City '{city}' not found. Please check the spelling and try again.")


st.title("MeteoMind")
city = st.text_input("Enter city name", "London")
record_audio=audio_recorder()

if st.button("Get Weather"):
    try:
        all_process(city,weather_api_key,choice="text")
    except Exception as e :
        st.write(f"Error found {e}")
        
        
elif record_audio:
    city=recognize_speech()
    try:
        all_process(city,weather_api_key,choice="audio")
    except Exception as e :
        st.write(f"Error found {e}")

