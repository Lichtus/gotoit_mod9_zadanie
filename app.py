from pathlib import Path
from typing import Literal, Optional

import instructor
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from langfuse.decorators import observe
from langfuse.openai import OpenAI
from pycaret.regression import load_model, predict_model
from pydantic import BaseModel, Field

from spaces_client import download_file

load_dotenv()

MODEL_SPACES_KEY = "models/polmaraton_model.pkl"
LOCAL_MODEL_PATH = Path("polmaraton_model.pkl")

FIELD_LABELS = {"gender": "płeć", "age": "wiek", "time_5k_minutes": "czas na 5 km"}
WELCOME_MESSAGE = (
    "Cześć! Przedstaw się — podaj swoją płeć, wiek i czas na 5 km, "
    "a oszacuję Twój czas na półmaratonie."
)


class ExtractedInfo(BaseModel):
    gender: Optional[Literal["M", "K"]] = Field(
        None, description="Płeć: M (mężczyzna) lub K (kobieta)"
    )
    age: Optional[int] = Field(None, description="Wiek w latach")
    time_5k_minutes: Optional[float] = Field(
        None, description="Czas na 5 km w minutach, może mieć część dziesiętną, np. 27.5"
    )


@st.cache_resource
def get_model():
    if not LOCAL_MODEL_PATH.exists():
        download_file(MODEL_SPACES_KEY, LOCAL_MODEL_PATH)
    return load_model(str(LOCAL_MODEL_PATH.with_suffix("")))


@observe()
def extract_info(text: str) -> ExtractedInfo:
    client = instructor.from_openai(OpenAI())
    return client.chat.completions.create(
        model="gpt-4o-mini",
        response_model=ExtractedInfo,
        messages=[
            {
                "role": "system",
                "content": (
                    "Wyciągnij z tekstu użytkownika płeć (M lub K), wiek w latach "
                    "i czas na 5 km w minutach. Jeśli którejś informacji nie ma "
                    "w tekście, zostaw odpowiednie pole jako null."
                ),
            },
            {"role": "user", "content": text},
        ],
    )


def format_seconds(total_seconds: float) -> str:
    total_seconds = int(round(total_seconds))
    h, rem = divmod(total_seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def missing_field_labels(info: dict) -> list[str]:
    return [FIELD_LABELS[field] for field, value in info.items() if value is None]


def reset_conversation():
    st.session_state.messages = [{"role": "assistant", "content": WELCOME_MESSAGE}]
    st.session_state.collected_info = {"gender": None, "age": None, "time_5k_minutes": None}
    st.session_state.prediction_done = False


st.set_page_config(page_title="Kalkulator czasu półmaratonu")
st.title("Kalkulator czasu półmaratonu")

if "messages" not in st.session_state:
    reset_conversation()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if st.session_state.prediction_done:
    if st.button("Nowe zapytanie"):
        reset_conversation()
        st.rerun()
else:
    user_text = st.chat_input("Twoja odpowiedź")
    if user_text:
        st.session_state.messages.append({"role": "user", "content": user_text})

        with st.spinner("Analizuję..."):
            extracted = extract_info(user_text)

        for field in st.session_state.collected_info:
            value = getattr(extracted, field)
            if value is not None:
                st.session_state.collected_info[field] = value

        missing = missing_field_labels(st.session_state.collected_info)
        if missing:
            reply = f"Dzięki! Brakuje mi jeszcze: {', '.join(missing)}. Podasz?"
        else:
            info = st.session_state.collected_info
            time_5k_s = round(info["time_5k_minutes"] * 60)
            input_df = pd.DataFrame(
                [{"gender": info["gender"], "age": info["age"], "time_5k_s": time_5k_s}]
            )

            model = get_model()
            prediction = predict_model(model, data=input_df)
            predicted_seconds = prediction["prediction_label"].iloc[0]

            reply = f"Szacowany czas półmaratonu: **{format_seconds(predicted_seconds)}**"
            st.session_state.prediction_done = True

        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.rerun()
