import streamlit as st
import base64
import requests
import io
from PIL import Image

# ---------------------------------------
# PAGE CONFIG
# ---------------------------------------
st.set_page_config(
    page_title="AI Portrait Stylizer",
    page_icon="🎨",
    layout="centered"
)

st.title("🎨 AI Portrait Stylizer")
st.write("Upload your photo → choose a style → generate an AI art portrait.")

# ---------------------------------------
# READ API KEYS (OpenAI + Replicate)
# ---------------------------------------
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", "")
REPLICATE_API_TOKEN = st.secrets.get("REPLICATE_API_TOKEN", "")

# Allow user override
openai_manual = st.sidebar.text_input("Optional: Enter OpenAI API Key", type="password")
if openai_manual:
    OPENAI_API_KEY = openai_manual

replicate_manual = st.sidebar.text_input("Optional: Enter Replicate API Token", type="password")
if replicate_manual:
    REPLICATE_API_TOKEN = replicate_manual

# ---------------------------------------
# MODEL SELECTION
# ---------------------------------------
provider = st.sidebar.selectbox(
    "Choose AI Model Provider",
    ["OpenAI (DALL·E 3)", "Replicate (Stable Diffusion XL)"]
)

# ---------------------------------------
# STYLE PRESETS
# ---------------------------------------
styles = {
    "✨ Cinematic Portrait": "A cinematic photography portrait, dramatic lighting, 85mm lens, ultra-clear skin, realistic tones.",
    "🖌 Watercolor Painting": "Watercolor fine-art portrait, soft edges, pastel color palette, delicate textures.",
    "🌌 Cyberpunk Neon": "Cyberpunk portrait with neon lights, futuristic city glow, high contrast, glowing edges.",
    "🎎 Studio K-Beauty": "Korean studio beauty portrait, soft light, minimalistic, clean skin retouching, Vogue style.",
}

style_name = st.selectbox("Choose a Style", list(styles.keys()))
style_prompt = styles[style_name]

# ---------------------------------------
# IMAGE UPLOAD
# ---------------------------------------
uploaded_img = st.file_uploader("Upload your photo", type=["jpg", "jpeg", "png"])

def image_to_base64(img):
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


# ---------------------------------------
# OPENAI IMAGE GENERATION
# ---------------------------------------
def generate_openai(img, style_prompt):
    if OPENAI_API_KEY == "":
        st.error("Missing OPENAI_API_KEY in Secrets or input field.")
        return None

    img_b64 = image_to_base64(img)

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_API_KEY}"}

    payload = {
        "model": "gpt-image-1",
        "prompt": f"Transform this image into: {style_prompt}",
        "image": img_b64,
        "size": "1024x1024"
    }

    res = requests.post(
        "https://api.openai.com/v1/images/edits",
        headers=headers,
        json=payload
    )

    if res.status_code != 200:
        st.error(res.text)
        return None

    output_b64 = res.json()['data'][0]['b64_json']
    return Image.open(io.BytesIO(base64.b64decode(output_b64)))


# ---------------------------------------
# REPLICATE IMAGE GENERATION
# ---------------------------------------
def generate_replicate(img, style_prompt):
    if REPLICATE_API_TOKEN == "":
        st.error("Missing REPLICATE_API_TOKEN in Secrets or input field.")
        return None

    img_b64 = image_to_base64(img)

    headers = {
        "Authorization": f"Token {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "version": "5c7ac13cfa6f9693cdd09312edc9c305",  # SDXL
        "input": {
            "prompt": style_prompt,
            "image": img_b64,
            "num_inference_steps": 40
        }
    }

    res = requests.post("https://api.replicate.com/v1/predictions", json=payload, headers=headers)

    if res.status_code != 201:
        st.error(res.text)
        return None

    # Poll for result
    prediction = res.json()
    get_url = prediction["urls"]["get"]

    while True:
        poll = requests.get(get_url, headers=headers).json()
        if poll["status"] == "succeeded":
            output_url = poll["output"][0]
            break
        elif poll["status"] == "failed":
            st.error("Generation failed.")
            return None

    img_data = requests.get(output_url).content
    return Image.open(io.BytesIO(img_data))


# ---------------------------------------
# GENERATE BUTTON
# ---------------------------------------
if uploaded_img:
    st.image(uploaded_img, caption="Uploaded Image", width=300)
    gen = st.button("Generate AI Portrait ✨")

    if gen:
        with st.spinner("Generating your AI portrait..."):

            img = Image.open(uploaded_img)

            if provider.startswith("OpenAI"):
                result = generate_openai(img, style_prompt)
            else:
                result = generate_replicate(img, style_prompt)

            if result:
                st.success("Done!")
                st.image(result, caption="AI Stylized Portrait", width=400)

                # Download button
                buf = io.BytesIO()
                result.save(buf, format="PNG")
                st.download_button(
                    "Download Image",
                    data=buf.getvalue(),
                    file_name="ai_portrait.png",
                    mime="image/png"
                )

