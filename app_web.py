import os
import tempfile
import zipfile
import cv2
import numpy as np
import streamlit as st
from PIL import Image
import urllib.request
import urllib.parse
import json
from datetime import datetime, timedelta

# Import sécurisé de MoviePy
try:
    from moviepy import VideoFileClip, ImageClip, CompositeVideoClip
except ImportError:
    from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip

st.set_page_config(page_title="Studio TikTok Mobile", page_icon="🎬", layout="centered")

# Dossiers
dossier_actuel = os.path.dirname(os.path.abspath(__file__))
dossier_brutes_standard = os.path.join(dossier_actuel, "videos_brutes")
dossier_brutes_recadrage = os.path.join(dossier_actuel, "videos_brutes_recadrage")
dossier_brutes_reallift00n = os.path.join(dossier_actuel, "videos_brutes_reallift00n")
dossier_sortie = os.path.join(dossier_actuel, "videos_finales")

chemin_logo = os.path.join(dossier_actuel, "logo.png")
chemin_logo2 = os.path.join(dossier_actuel, "logo2.png")
chemin_config = os.path.join(dossier_actuel, "config.txt")

for d in [dossier_brutes_standard, dossier_brutes_recadrage, dossier_brutes_reallift00n, dossier_sortie]:
    os.makedirs(d, exist_ok=True)

FIN_LOGO_1 = 5.97             
DEBUT_LOGO_2 = 5.92           
TAILLE_LOGO_REALLIFT00N = 440 
POS_A = (86, 610)             
POS_B = (485, 861)            

def couper_video(video, debut, fin):
    try:
        return video.subclipped(debut, fin) if fin > 0 else video
    except AttributeError:
        return video.subclip(debut, fin) if fin > 0 else video

def redimensionner_image_clip(clip, width=None, height=None):
    try:
        return clip.resized(width=width, height=height, apply_to=['mask'], resample='bicubic')
    except AttributeError:
        try:
            return clip.resize(width=width, height=height, apply_to=['mask'])
        except:
            return clip.resize(width=width, height=height)

def definir_duree(clip, duree):
    try:
        return clip.with_duration(duree)
    except AttributeError:
        return clip.set_duration(duree)

def definir_debut(clip, debut):
    try:
        return clip.with_start(debut)
    except AttributeError:
        return clip.set_start(debut)

def positionner_clip(clip, pos):
    try:
        return clip.with_position(pos)
    except AttributeError:
        return clip.set_position(pos)

def rogner_video(video, x1, y1, x2, y2):
    try:
        return video.cropped(x1=x1, y1=y1, x2=x2, y2=y2)
    except AttributeError:
        return video.crop(x1=x1, y1=y1, x2=x2, y2=y2)

def obtenir_logo_detoure(chemin_img):
    if not os.path.exists(chemin_img):
        return chemin_img
    img = cv2.imread(chemin_img, cv2.IMREAD_UNCHANGED)
    if img is None:
        return chemin_img
    if img.shape[2] == 3:
        b, g, r = cv2.split(img)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, alpha = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)
        img_rgba = cv2.merge([b, g, r, alpha])
    else:
        img_rgba = img
    chemin_temp_propre = os.path.join(tempfile.gettempdir(), "logo_detoure.png")
    cv2.imwrite(chemin_temp_propre, img_rgba)
    return chemin_temp_propre

def lire_coordonnees():
    if os.path.exists(chemin_config):
        try:
            with open(chemin_config, "r") as f:
                contenu = f.read().strip()
                x_str, y_str = contenu.split(",")
                return int(x_str), int(y_str)
        except:
            pass
    return 172, 344

# Fonction de récupération blindée avec secours automatique
def recuperer_miniatures_radar(api_key, mode_recent=True):
    toutes_les_videos = []
    createurs_cibles = [
        "Squeezie", "Mastu", "Legend Guillaume Pley", "McFly Carlito", 
        "Zack Nani", "Popcorn talk", "Alex Hitchens", "Goldenboy", 
        "Giuseppe", "Inoxtag", "Amixem", "Vincent Lapierre", "Micode",
        "HugoDécrypte", "Joyca", "Michou", "Theodort"
    ]
    
    for createur in createurs_cibles:
        try:
            query = urllib.parse.quote(createur)
            
            # Première tentative avec les critères choisis
            url = (
                f"https://www.googleapis.com/youtube/v3/search?part=snippet"
                f"&q={query}&type=video&regionCode=FR&relevanceLanguage=fr"
                f"&videoDuration=medium&maxResults=2&key={api_key}"
            )
            
            if mode_recent:
                date_limite = (datetime.utcnow() - timedelta(days=7)).isoformat("T") + "Z"
                url += f"&publishedAfter={date_limite}&order=date"
            else:
                url += "&order=viewCount"

            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode())
            
            items = data.get("items", [])
            
            # SÉCURITÉ DE SECOURS : Si le mode récent ne renvoie rien pour ce créateur, on élargit sans limite de temps
            if not items and mode_recent:
                url_secours = (
                    f"https://www.googleapis.com/youtube/v3/search?part=snippet"
                    f"&q={query}&type=video&regionCode=FR&relevanceLanguage=fr"
                    f"&videoDuration=medium&maxResults=1&order=viewCount&key={api_key}"
                )
                req_secours = urllib.request.Request(url_secours, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req_secours, timeout=4) as resp_secours:
                    data_secours = json.loads(resp_secours.read().decode())
                items = data_secours.get("items", [])

            for item in items:
                vid_id = item.get("id", {}).get("videoId")
                if not vid_id:
                    continue
                snippet = item.get("snippet", {})
                thumbnails = snippet.get("thumbnails", {})
                thumb_url = thumbnails.get("high", {}).get("url") or thumbnails.get("medium", {}).get("url")
                
                if thumb_url:
                    toutes_les_videos.append({
                        "title": snippet.get("title", "Sans titre"),
                        "author": snippet.get("channelTitle", createur),
                        "link": f"https://www.youtube.com/watch?v={vid_id}",
                        "thumbnail": thumb_url,
                        "publish_time": snippet.get("publishTime", "")
                    })
        except Exception:
            continue
            
    videos_uniques = {v['link']: v for v in toutes_les_videos}.values()
    liste_finale = list(videos_uniques)
    if mode_recent and liste_finale:
        liste_finale.sort(key=lambda x: x["publish_time"], reverse=True)
    return liste_finale

# Navigation
st.sidebar.title("📌 Menu Principal")
section_principale = st.sidebar.radio(
    "Que souhaites-tu faire ?",
    ["🎬 Montage Vidéo", "🔥 Radar Culture Jeune FR"]
)

if section_principale == "🎬 Montage Vidéo":
    st.title("🎬 Studio TikTok - Web & Mobile")
    option = st.selectbox(
        "Choisis ton mode de traitement :", 
        ["Traitement Standard", "Traitement avec Recadrage", "Traitement reallift00n"]
    )
    uploaded_files = st.file_uploader("Sélectionne tes vidéos brutes (.mp4)", type=["mp4"], accept_multiple_files=True)
    
    if uploaded_files:
        st.success(f"{len(uploaded_files)} vidéo(s) prête(s) !")
        if st.button("🚀 Lancer le montage"):
            st.write("Traitement en cours...")

else:
    st.title("🔥 Radar Culture Jeune FR - Galerie Visuelle")
    api_key = st.secrets.get("YOUTUBE_API_KEY", "")

    if api_key:
        choix_periode = st.radio(
            "Période des vidéos :",
            ["⚡ Sorties Récentes (< 7 jours)", "🏆 Best-Of Historique"],
            horizontal=True
        )
        mode_recent = True if "Récentes" in choix_periode else False

        if st.button("🔄 Actualiser / Charger les miniatures", type="primary"):
            with st.spinner("Chargement des miniatures..."):
                st.session_state['galerie_videos'] = recuperer_miniatures_radar(api_key, mode_recent=mode_recent)

        if 'galerie_videos' in st.session_state and st.session_state['galerie_videos']:
            st.success(f"🖼️ {len(st.session_state['galerie_videos'])} miniatures affichées !")
            cols = st.columns(2)
            for idx, vid in enumerate(st.session_state['galerie_videos']):
                with cols[idx % 2]:
                    st.image(vid['thumbnail'], use_column_width=True)
                    st.markdown(f"**{vid['title']}**")
                    st.caption(f"📺 {vid['author']}")
                    st.link_button("▶️ Voir sur YouTube", vid['link'], key=f"btn_mini_{idx}")
                    st.markdown("---")
        else:
            st.info("Clique sur **🔄 Actualiser** pour afficher la grille.")
    else:
        st.warning("⚠️ Clé `YOUTUBE_API_KEY` introuvable dans les Secrets de Streamlit.")
