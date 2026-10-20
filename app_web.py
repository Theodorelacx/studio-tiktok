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

# Import sécurisé de MoviePy pour compatibilité PC / Cloud
try:
    from moviepy import VideoFileClip, ImageClip, CompositeVideoClip
except ImportError:
    from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip

# Configuration de la page web
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

# -------------------------------------------------------------------------
# PARAMÈTRES FINAUX REALLIFT00N (VERROUILLÉ ET INTACT)
# -------------------------------------------------------------------------
FIN_LOGO_1 = 5.97             
DEBUT_LOGO_2 = 5.92           
TAILLE_LOGO_REALLIFT00N = 440 
POS_A = (86, 610)             
POS_B = (485, 861)            
# -------------------------------------------------------------------------

# Fonctions utilitaires MoviePy
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

# Fonction robuste pour récupérer les miniatures des créateurs phares
def recuperer_miniatures_radar(api_key, mode_recent=True):
    toutes_les_videos = []
    
    # Liste complète de l'écosystème web français (15-30 ans)
    createurs_cibles = [
        "Squeezie", "Mastu", "Legend Guillaume Pley", "McFly Carlito", 
        "Zack Nani", "Popcorn talk", "Alex Hitchens", "Goldenboy", 
        "Giuseppe", "Inoxtag", "Amixem", "Vincent Lapierre", "Micode",
        "HugoDécrypte", "Joyca", "Michou", "Theodort"
    ]
    
    for createur in createurs_cibles:
        try:
            query = urllib.parse.quote(createur)
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
            
            for item in data.get("items", []):
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
            
    # Dédoublonnage par lien et tri
    videos_uniques = {v['link']: v for v in toutes_les_videos}.values()
    liste_finale = list(videos_uniques)
    if mode_recent and liste_finale:
        liste_finale.sort(key=lambda x: x["publish_time"], reverse=True)
    return liste_finale

# =========================================================================
# NAVIGATION PRINCIPALE
# =========================================================================
st.sidebar.title("📌 Menu Principal")
section_principale = st.sidebar.radio(
    "Que souhaites-tu faire ?",
    ["🎬 Montage Vidéo", "🔥 Radar Culture Jeune FR"]
)

# -------------------------------------------------------------------------
# SECTION 1 : MONTAGE VIDÉO
# -------------------------------------------------------------------------
if section_principale == "🎬 Montage Vidéo":
    st.title("🎬 Studio TikTok - Web & Mobile")
    st.write("Pilote ton studio de montage depuis ton PC ou ton téléphone !")

    option = st.selectbox(
        "Choisis ton mode de traitement :", 
        ["Traitement Standard", "Traitement avec Recadrage", "Traitement reallift00n"]
    )

    st.subheader("1. Sélectionne tes vidéos brutes")
    uploaded_files = st.file_uploader("Glisse ou sélectionne tes vidéos brutes (.mp4)", type=["mp4"], accept_multiple_files=True)

    if "centre_x" not in st.session_state or "centre_y" not in st.session_state:
        cx_def, cy_def = lire_coordonnees()
        st.session_state.centre_x = cx_def
        st.session_state.centre_y = cy_def

    if uploaded_files and option == "Traitement Standard":
        st.markdown("---")
        st.subheader("2. Calage du Logo (Standard)")
        premiere_video = uploaded_files[0]
        bytes_data = premiere_video.getvalue()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
            tmp_file.write(bytes_data)
            tmp_path = tmp_file.name

        cap = cv2.VideoCapture(tmp_path)
        ret, frame = cap.read()
        cap.release()
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass

        if ret:
            h_orig, w_orig = frame.shape[:2]
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            TAILLE_LOGO_STD = 200
            rayon = int(TAILLE_LOGO_STD / 2)
            
            col1, col2 = st.columns(2)
            with col1:
                st.session_state.centre_x = st.slider("Centre X (Horizontal)", 0, w_orig, st.session_state.centre_x)
            with col2:
                st.session_state.centre_y = st.slider("Centre Y (Vertical)", 0, h_orig, st.session_state.centre_y)
                
            frame_apercu = frame_rgb.copy()
            cv2.circle(frame_apercu, (st.session_state.centre_x, st.session_state.centre_y), rayon, (0, 255, 0), 4)
            cv2.circle(frame_apercu, (st.session_state.centre_x, st.session_state.centre_y), 8, (255, 0, 0), -1)
            st.image(Image.fromarray(frame_apercu), caption=f"Aperçu du Centre : X={st.session_state.centre_x}, Y={st.session_state.centre_y}", use_column_width=True)

            with open(chemin_config, "w") as f:
                f.write(f"{st.session_state.centre_x},{st.session_state.centre_y}")

    elif option == "Traitement reallift00n":
        if not os.path.exists(chemin_logo2) and not os.path.exists(chemin_logo2.replace(".png", ".jpg")):
            st.warning("⚠️ Attention : Le fichier `logo2.png` n'a pas été trouvé dans le dossier du projet.")

    if uploaded_files:
        st.markdown("---")
        st.subheader("3. Lancement du montage")
        st.success(f"{len(uploaded_files)} vidéo(s) prête(s) à être traitée(s) !")
        
        if st.button("🚀 Lancer le montage ultra-rapide"):
            barre_progression = st.progress(0)
            statut_texte = st.empty()
            total = len(uploaded_files)
            
            for index, uploaded_file in enumerate(uploaded_files):
                if option == "Traitement Standard":
                    dossier_destination = dossier_brutes_standard
                elif option == "Traitement avec Recadrage":
                    dossier_destination = dossier_brutes_recadrage
                else:
                    dossier_destination = dossier_brutes_reallift00n

                chemin_in = os.path.join(dossier_destination, uploaded_file.name)
                with open(chemin_in, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                statut_texte.text(f"Montage optimisé de : {uploaded_file.name} ({index+1}/{total})...")
                nom_propre = os.path.splitext(uploaded_file.name)[0].replace("_", " ")
                chemin_out = os.path.join(dossier_sortie, f"{nom_propre}.mp4")
                video = VideoFileClip(chemin_in)
                
                if option == "Traitement reallift00n":
                    video_traitee = video
                    logo_brut = chemin_logo2
                    if not os.path.exists(logo_brut):
                        logo_brut_jpg = chemin_logo2.replace(".png", ".jpg")
                        if os.path.exists(logo_brut_jpg):
                            logo_brut = logo_brut_jpg
                        else:
                            logo_brut = chemin_logo
                    
                    logo_file = obtenir_logo_detoure(logo_brut)
                    duree_p1 = min(FIN_LOGO_1, video_traitee.duration)
                    coin_a_x = POS_A[0] - int(TAILLE_LOGO_REALLIFT00N / 2)
                    coin_a_y = POS_A[1] - int(TAILLE_LOGO_REALLIFT00N / 2)
                    
                    logo_p1_img = ImageClip(logo_file)
                    logo_p1_img = definir_duree(logo_p1_img, duree_p1)
                    logo_p1_res = redimensionner_image_clip(logo_p1_img, width=TAILLE_LOGO_REALLIFT00N)
                    logo_part1 = positionner_clip(logo_p1_res, (coin_a_x, coin_a_y))
                    elements_composite = [video_traitee, logo_part1]
                    
                    if video_traitee.duration > DEBUT_LOGO_2:
                        duree_p2 = video_traitee.duration - DEBUT_LOGO_2
                        coin_b_x = POS_B[0] - int(TAILLE_LOGO_REALLIFT00N / 2)
                        coin_b_y = POS_B[1] - int(TAILLE_LOGO_REALLIFT00N / 2)
                        logo_p2_img = ImageClip(logo_file)
                        logo_p2_img = definir_debut(logo_p2_img, DEBUT_LOGO_2)
                        logo_p2_img = definir_duree(logo_p2_img, duree_p2)
                        logo_p2_res = redimensionner_image_clip(logo_p2_img, width=TAILLE_LOGO_REALLIFT00N)
                        logo_part2 = positionner_clip(logo_p2_res, (coin_b_x, coin_b_y))
                        elements_composite.append(logo_part2)
                    
                    video_finale = CompositeVideoClip(elements_composite, size=video_traitee.size)
                
                elif option == "Traitement Standard":
                    nouvelle_duree = video.duration - 3
                    video_coupee = couper_video(video, 0, nouvelle_duree)
                    logo_img = ImageClip(chemin_logo)
                    logo_img = definir_duree(logo_img, video_coupee.duration)
                    logo_res = redimensionner_image_clip(logo_img, width=200)

                    if os.path.exists(chemin_config):
                        with open(chemin_config, "r") as f:
                            cx, cy = map(int, f.read().split(","))
                            x_coin = cx - 100
                            y_coin = cy - 100
                    else:
                        x_coin, y_coin = 0, 0
                    
                    logo = positionner_clip(logo_res, (x_coin, y_coin))
                    video_finale = CompositeVideoClip([video_coupee, logo], size=video_coupee.size)
                
                else: 
                    nouvelle_duree = video.duration - 3
                    video_coupee = couper_video(video, 0, nouvelle_duree)
                    largeur, hauteur = video_coupee.size
                    video_recadree = rogner_video(video_coupee, 0, 120, largeur, hauteur)
                    logo_img = ImageClip(chemin_logo)
                    logo_img = definir_duree(logo_img, video_recadree.duration)
                    logo_res = redimensionner_image_clip(logo_img, width=150)
                    logo = positionner_clip(logo_res, (20, 20))
                    video_finale = CompositeVideoClip([video_recadree, logo], size=video_recadree.size)
                
                temp_audio = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False).name
                try:
                    video_finale.write_videofile(
                        chemin_out, fps=30, codec='libx264', audio_codec='aac', 
                        bitrate='10000k', preset='medium', threads=4, temp_audiofile=temp_audio, logger=None
                    )
                finally:
                    if os.path.exists(temp_audio):
                        try: os.remove(temp_audio)
                        except: pass
                
                video.close()
                video_finale.close()
                barre_progression.progress((index + 1) / total)
                
            st.success("🎉 Tous les montages sont terminés à vitesse maximale !")

    st.markdown("---")
    st.subheader("📥 Gestion des vidéos finales")
    fichiers_finaux = [f for f in os.listdir(dossier_sortie) if f.endswith(".mp4")]

    if fichiers_finaux:
        st.write("Coche les vidéos que tu souhaites gérer :")
        fichiers_selectionnes = []
        for f_fini in fichiers_finaux:
            col_chk, col_dl = st.columns([4, 1])
            with col_chk:
                isSelected = st.checkbox(f"🎬 {f_fini}", key=f"chk_{f_fini}")
                if isSelected:
                    fichiers_selectionnes.append(f_fini)
            with col_dl:
                chemin_f_fini = os.path.join(dossier_sortie, f_fini)
                with open(chemin_f_fini, "rb") as fichier_ouvert:
                    st.download_button(label="📥", data=fichier_ouvert, file_name=f_fini, mime="video/mp4", key=f"dl_{f_fini}")

        st.markdown("---")
        col_action1, col_action2 = st.columns(2)
        with col_action1:
            if fichiers_selectionnes:
                zip_path = os.path.join(dossier_actuel, "videos_selectionnees.zip")
                with zipfile.ZipFile(zip_path, "w") as zipf:
                    for f_sel in fichiers_selectionnes:
                        zipf.write(os.path.join(dossier_sortie, f_sel), arcname=f_sel)
                with open(zip_path, "rb") as z_file:
                    st.download_button(
                        label=f"📦 Télécharger la sélection en ZIP ({len(fichiers_selectionnes)})",
                        data=z_file, file_name="videos_tiktok_selection.zip", mime="application/zip", type="primary"
                    )
            else:
                st.info("Coche au moins une vidéo pour activer le téléchargement groupé.")

        with col_action2:
            if fichiers_selectionnes:
                if st.button("🗑️ Supprimer la sélection", type="secondary"):
                    import gc
                    gc.collect()
                    for f_sel in fichiers_selectionnes:
                        chemin_a_supprimer = os.path.join(dossier_sortie, f_sel)
                        if os.path.exists(chemin_a_supprimer):
                            try: os.remove(chemin_a_supprimer)
                            except: pass
                    st.success("Opération de suppression terminée !")
                    st.rerun()
    else:
        st.info("Aucune vidéo finale pour le moment.")

# -------------------------------------------------------------------------
# SECTION 2 : RADAR CULTURE JEUNE FR (GALERIE DE MINIATURES STABILISÉE)
# -------------------------------------------------------------------------
else:
    st.title("🔥 Radar Culture Jeune FR - Galerie Visuelle")
    st.write("Galerie de miniatures officielles de l'écosystème web français. Clique sur **Actualiser** pour lancer ou rafraîchir la veille.")

    api_key = st.secrets.get("YOUTUBE_API_KEY", "")

    if api_key:
        choix_periode = st.radio(
            "Période des vidéos :",
            ["⚡ Sorties Récentes (Moins de 7 jours)", "🏆 Best-Of Historique (Toutes les plus vues)"],
            horizontal=True
        )
        mode_recent = True if "Récentes" in choix_periode else False

        # Bouton d'actualisation propre relié au state
        if st.button("🔄 Actualiser / Charger les miniatures", type="primary"):
            with st.spinner("Récupération des miniatures en cours..."):
                st.session_state['galerie_videos'] = recuperer_miniatures_radar(api_key, mode_recent=mode_recent)

        # Affichage sécurisé de la galerie
        if 'galerie_videos' in st.session_state and st.session_state['galerie_videos']:
            st.success(f"🖼️ {len(st.session_state['galerie_videos'])} miniatures chargées !")
            cols = st.columns(2)
            for idx, vid in enumerate(st.session_state['galerie_videos']):
                with cols[idx % 2]:
                    st.image(vid['thumbnail'], use_column_width=True)
                    st.markdown(f"**{vid['title']}**")
                    st.caption(f"📺 {vid['author']}")
                    st.link_button("▶️ Voir sur YouTube", vid['link'], key=f"btn_mini_{idx}")
                    st.markdown("---")
        else:
            st.info("💡 Clique sur **🔄 Actualiser / Charger les miniatures** pour afficher la grille.")
    else:
        st.warning("⚠️ Clé `YOUTUBE_API_KEY` introuvable dans les Secrets de Streamlit Cloud.")
