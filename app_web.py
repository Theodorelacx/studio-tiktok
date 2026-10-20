import os
import tempfile
import zipfile
import cv2
import numpy as np
import streamlit as st
from PIL import Image
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
FIN_LOGO_1 = 5.97             # Le premier logo reste jusqu'à 5.97s
DEBUT_LOGO_2 = 5.92           # Le second logo démarre dès 5.92s (chevauchement)
TAILLE_LOGO_REALLIFT00N = 440 # Taille du logo reallift00n
POS_A = (86, 610)             # Position 1 - X=86, Y=610
POS_B = (485, 861)            # Position 2 - X=485, Y=861
# -------------------------------------------------------------------------

# Fonction pour transformer le fond noir en transparence (détourage parfait)
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

# Fonction pour lire config.txt (pour le mode Standard)
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

st.title("🎬 Studio TikTok - Web & Mobile")
st.write("Pilote ton studio de montage depuis ton PC ou ton téléphone !")

# Menu de choix
option = st.selectbox(
    "Choisis ton mode de traitement :", 
    ["Traitement Standard", "Traitement avec Recadrage", "Traitement reallift00n"]
)

# Zone d'envoi des vidéos
st.subheader("1. Sélectionne tes vidéos brutes")
uploaded_files = st.file_uploader("Glisse ou sélectionne tes vidéos brutes (.mp4)", type=["mp4"], accept_multiple_files=True)

# Initialisation de la session state pour stocker les coordonnées du centre (Mode Standard)
if "centre_x" not in st.session_state or "centre_y" not in st.session_state:
    cx_def, cy_def = lire_coordonnees()
    st.session_state.centre_x = cx_def
    st.session_state.centre_y = cy_def

# Calage du Logo - Uniquement pour le Traitement Standard
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

# Section Lancement du montage
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
            
            # --- TRAITEMENT REALLIFT00N (INTOUCHÉ) ---
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
                
                logo_part1 = (
                    ImageClip(logo_file)
                    .with_duration(duree_p1)
                    .resized(width=TAILLE_LOGO_REALLIFT00N)
                    .with_position((coin_a_x, coin_a_y))
                )
                
                elements_composite = [video_traitee, logo_part1]
                
                if video_traitee.duration > DEBUT_LOGO_2:
                    duree_p2 = video_traitee.duration - DEBUT_LOGO_2
                    coin_b_x = POS_B[0] - int(TAILLE_LOGO_REALLIFT00N / 2)
                    coin_b_y = POS_B[1] - int(TAILLE_LOGO_REALLIFT00N / 2)
                    
                    logo_part2 = (
                        ImageClip(logo_file)
                        .with_start(DEBUT_LOGO_2)
                        .with_duration(duree_p2)
                        .resized(width=TAILLE_LOGO_REALLIFT00N)
                        .with_position((coin_b_x, coin_b_y))
                    )
                    elements_composite.append(logo_part2)
                
                video_finale = CompositeVideoClip(elements_composite, size=video_traitee.size)
            
            # --- TRAITEMENT STANDARD (RETABLI PROPREMENT) ---
            elif option == "Traitement Standard":
                nouvelle_duree = video.duration - 3
                video_coupee = video.subclipped(0, nouvelle_duree) if nouvelle_duree > 0 else video
                
                logo = ImageClip(chemin_logo).with_duration(video_coupee.duration).resized(width=200)
                if os.path.exists(chemin_config):
                    with open(chemin_config, "r") as f:
                        cx, cy = map(int, f.read().split(","))
                        x_coin = cx - 100
                        y_coin = cy - 100
                else:
                    x_coin, y_coin = 0, 0
                logo = logo.with_position((x_coin, y_coin))
                video_finale = CompositeVideoClip([video_coupee, logo], size=video_coupee.size)
            
            # --- TRAITEMENT AVEC RECADRAGE ---
            else: 
                nouvelle_duree = video.duration - 3
                video_coupee = video.subclipped(0, nouvelle_duree) if nouvelle_duree > 0 else video
                largeur, hauteur = video_coupee.size
                video_recadree = video_coupee.cropped(x1=0, y1=120, x2=largeur, y2=hauteur)
                logo = ImageClip(chemin_logo).with_duration(video_recadree.duration).resized(width=150)
                logo = logo.with_position((20, 20))
                video_finale = CompositeVideoClip([video_recadree, logo], size=video_recadree.size)
            
            temp_audio = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False).name
            try:
                video_finale.write_videofile(
                    chemin_out, 
                    fps=30, 
                    codec='libx264', 
                    audio_codec='aac', 
                    bitrate='6000k', 
                    preset='fast',
                    threads=4,
                    temp_audiofile=temp_audio, 
                    logger=None
                )
            finally:
                if os.path.exists(temp_audio):
                    try: os.remove(temp_audio)
                    except: pass
            
            video.close()
            video_finale.close()
            barre_progression.progress((index + 1) / total)
            
        st.success("🎉 Tous les montages sont terminés à vitesse maximale !")

# Section de gestion et téléchargement des vidéos finales
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
                    data=z_file,
                    file_name="videos_tiktok_selection.zip",
                    mime="application/zip",
                    type="primary"
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
                        try:
                            os.remove(chemin_a_supprimer)
                        except Exception as e:
                            try:
                                os.chmod(chemin_a_supprimer, 0o777)
                                os.remove(chemin_a_supprimer)
                            except:
                                st.error(f"Impossible de supprimer {f_sel} : le fichier est verrouillé.")
                st.success("Opération de suppression terminée !")
                st.rerun()

else:
    st.info("Aucune vidéo finale pour le moment.")
