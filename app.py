import streamlit as st
import sqlite3
import pandas as pd
import re
import requests

def clean_chassis(s):
    if not s: return None
    # Garder uniquement les chiffres
    return "".join(re.findall(r'\d+', str(s)))

# --- SUPABASE CLOUD BACKUP HELPERS ---
def get_supabase_config():
    if "supabase" in st.secrets:
        return st.secrets["supabase"]["url"], st.secrets["supabase"]["key"]
    return None, None

def supabase_select(table_name):
    url, key = get_supabase_config()
    if not url or not key:
        return None
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}"
    }
    try:
        response = requests.get(f"{url}/rest/v1/{table_name.lower()}", headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None

def supabase_upsert(table_name, data):
    url, key = get_supabase_config()
    if not url or not key:
        return False
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }
    try:
        response = requests.post(f"{url}/rest/v1/{table_name.lower()}?on_conflict=code_place", json=data, headers=headers, timeout=5)
        return response.status_code in [200, 201]
    except Exception:
        return False

def supabase_insert(table_name, data):
    url, key = get_supabase_config()
    if not url or not key:
        return False
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(f"{url}/rest/v1/{table_name.lower()}", json=data, headers=headers, timeout=5)
        return response.status_code in [200, 201]
    except Exception:
        return False

def supabase_delete(table_name, code_place):
    url, key = get_supabase_config()
    if not url or not key:
        return False
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}"
    }
    try:
        response = requests.delete(f"{url}/rest/v1/{table_name.lower()}?code_place=eq.{code_place}", headers=headers, timeout=5)
        return response.status_code in [200, 204]
    except Exception:
        return False

def sync_from_supabase_if_empty(table_name):
    url, key = get_supabase_config()
    if not url or not key:
        return
    try:
        count = cursor.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        if count == 0:
            rows = supabase_select(table_name)
            if rows:
                for row in rows:
                    cursor.execute(
                        f"INSERT OR REPLACE INTO {table_name} (code_place, status, chassis) VALUES (?, ?, ?)",
                        (row.get("code_place"), row.get("status"), row.get("chassis"))
                    )
                conn.commit()
    except Exception:
        pass

def sync_history_from_supabase_if_empty():
    url, key = get_supabase_config()
    if not url or not key:
        return
    try:
        count = cursor.execute("SELECT COUNT(*) FROM history").fetchone()[0]
        if count == 0:
            rows = supabase_select("history")
            if rows:
                for row in rows:
                    cursor.execute(
                        "INSERT OR REPLACE INTO history (id, timestamp, username, park_name, action, code_place, old_chassis, new_chassis) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (row.get("id"), row.get("timestamp"), row.get("username"), row.get("park_name"), row.get("action"), row.get("code_place"), row.get("old_chassis"), row.get("new_chassis"))
                    )
                conn.commit()
    except Exception:
        pass



st.set_page_config(page_title="Gestion Parking", layout="wide")

# --- MODE MAINTENANCE ---
MAINTENANCE_MODE = False

if MAINTENANCE_MODE:
    st.title("🚧 Site en Maintenance / Restauration")
    st.warning("Le site est temporairement verrouillé pour maintenance et mise à jour de la base de données par l'administrateur. Veuillez ne pas effectuer de saisies pour le moment. L'accès sera rétabli d'ici quelques minutes. Merci de votre patience !")
    st.stop()


st.markdown("""
<style>
    /* Styling Streamlit UI */
    .stButton>button { border-radius: 8px; font-weight: 600; transition: all 0.3s ease; }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
    .stTextInput>div>div>input { border-radius: 8px; }
    .stSelectbox>div>div>div { border-radius: 8px; }
    div[data-testid="stMetric"] {
        background-color: #f8f9fa; padding: 15px; border-radius: 10px;
        border: 1px solid #dee2e6; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# Connexion DB
conn = sqlite3.connect("parking.db", check_same_thread=False)
cursor = conn.cursor()

# --- INIT HISTORY TABLE ---
cursor.execute("""
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    username TEXT,
    park_name TEXT,
    action TEXT,
    code_place TEXT,
    old_chassis TEXT,
    new_chassis TEXT
)
""")
conn.commit()
sync_history_from_supabase_if_empty()

# --- AUTHENTICATION LOGIC (SECURE WITH STREAMLIT SECRETS) ---
if "credentials" in st.secrets:
    credentials = st.secrets["credentials"]
else:
    credentials = {
        "MAN": "MAN2026",
        "yassine": "yassineMAN1",
        "amine": "amineMAN2"
    }

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""

def do_login():
    username = st.session_state.login_user
    password = st.session_state.login_pass
    if username in credentials and credentials[username] == password:
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.role = "admin" if username == "MAN" else "security"
    else:
        st.error("Identifiants incorrects.")


def do_logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""

if not st.session_state.logged_in:
    st.title("🔒 Connexion - Gestion Parking")
    st.text_input("Nom d'utilisateur", key="login_user")
    st.text_input("Mot de passe", type="password", key="login_pass")
    st.button("Se connecter", on_click=do_login)
    st.stop()

st.sidebar.markdown(f"👤 Connecté : **{st.session_state.username}**")
st.sidebar.button("Se déconnecter", on_click=do_logout)

if "supabase" in st.secrets:
    st.sidebar.success("☁️ Sauvegarde Supabase : Active")
else:
    st.sidebar.warning("⚠️ Sauvegarde Cloud : Non configurée")


if st.session_state.role == "admin":
    menu = st.sidebar.radio("Navigation :", ["🗺️ Parking", "📖 Historique"])
else:
    menu = "🗺️ Parking"

if menu == "📖 Historique":
    st.title("📖 Historique des Modifications")
    
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        try:
            with open("parking.db", "rb") as file:
                st.download_button(
                    label="💾 Télécharger SQLite (parking.db)",
                    data=file,
                    file_name="parking.db",
                    mime="application/x-sqlite3",
                    use_container_width=True
                )
        except Exception as e:
            st.error(f"Erreur de lecture SQLite : {e}")
            
    with col_dl2:
        try:
            import io
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer) as writer:
                # Onglet Historique
                history_df = pd.read_sql_query("SELECT datetime(timestamp, '+1 hour') as Date, username as Utilisateur, park_name as Parc, action as Action, code_place as Place, old_chassis as Ancien, new_chassis as Nouveau FROM history ORDER BY timestamp DESC", conn)
                history_df.to_excel(writer, sheet_name='Historique', index=False)
                
                # Onglets pour chaque parc
                all_parks = ["ECOMAIL", "TISSIR", "SEFAMAR", "V VLOG"]
                for p in all_parks:
                    t_name = "places" if p == "ECOMAIL" else f"places_{p.replace(' ', '_')}"
                    try:
                        df_p = pd.read_sql_query(f"SELECT code_place as Place, status as Statut, chassis as Chassis FROM {t_name}", conn)
                        df_p.to_excel(writer, sheet_name=p, index=False)
                    except:
                        pass
            
            st.download_button(
                label="📊 Exporter en Excel (.xlsx)",
                data=buffer.getvalue(),
                file_name="sauvegarde_parking_complet.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Erreur d'export Excel : {e}")
            
    st.markdown("### ☁️ Synchronisation Manuelle")
    if st.button("🔄 Synchroniser toute la base locale vers Supabase (Cloud)", use_container_width=True):
        url, key = get_supabase_config()
        if not url or not key:
            st.error("Clés Supabase non configurées.")
        else:
            with st.spinner("Synchronisation en cours..."):
                headers = {
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates"
                }
                success = True
                
                # Places tables
                all_parks = ["ECOMAIL", "TISSIR", "SEFAMAR", "V VLOG"]
                for p in all_parks:
                    t_name = "places" if p == "ECOMAIL" else f"places_{p.replace(' ', '_')}"
                    try:
                        cursor.execute(f"SELECT code_place, status, chassis FROM {t_name}")
                        rows = cursor.fetchall()
                        batch = [{"code_place": r[0], "status": r[1], "chassis": r[2]} for r in rows]
                        if batch:
                            resp = requests.post(f"{url}/rest/v1/{t_name.lower()}?on_conflict=code_place", json=batch, headers=headers, timeout=10)
                            if resp.status_code not in [200, 201]:
                                success = False
                                st.error(f"Erreur table {p} : {resp.status_code} - {resp.text}")
                    except Exception as e:
                        success = False
                        st.error(f"Erreur table {p} : {e}")
                
                # History table
                try:
                    cursor.execute("SELECT id, timestamp, username, park_name, action, code_place, old_chassis, new_chassis FROM history")
                    rows = cursor.fetchall()
                    batch = []
                    for h_id, ts, user, park_name, act, pl, old_ch, new_ch in rows:
                        batch.append({
                            "id": h_id,
                            "timestamp": ts,
                            "username": user,
                            "park_name": park_name,
                            "action": act,
                            "code_place": pl,
                            "old_chassis": old_ch,
                            "new_chassis": new_ch
                        })
                    if batch:
                        resp = requests.post(f"{url}/rest/v1/history", json=batch, headers=headers, timeout=10)
                        if resp.status_code not in [200, 201]:
                            success = False
                            st.error(f"Erreur historique : {resp.status_code} - {resp.text}")
                except Exception as e:
                    success = False
                    st.error(f"Erreur historique : {e}")
                
                if success:
                    st.success("✅ Synchronisation réussie de toutes les places et de l'historique vers Supabase !")

    st.markdown("---")
    history_df = pd.read_sql_query("SELECT datetime(timestamp, '+1 hour') as Date, username as Utilisateur, park_name as Parc, action as Action, code_place as Place, old_chassis as Ancien, new_chassis as Nouveau FROM history ORDER BY timestamp DESC", conn)
    st.dataframe(history_df, use_container_width=True)
    st.stop()

# ----------------------------

st.sidebar.title("🏢 Sélection du Parc")
park = st.sidebar.radio("Parcs disponibles :", ["ECOMAIL", "TISSIR", "SEFAMAR", "V VLOG"])

table_name = "places" if park == "ECOMAIL" else f"places_{park.replace(' ', '_')}"

cursor.execute(f"""
CREATE TABLE IF NOT EXISTS {table_name} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code_place TEXT UNIQUE,
    status TEXT,
    chassis TEXT
)
""")
conn.commit()
sync_from_supabase_if_empty(table_name)

# Nettoyage automatique de la base existante (supprimer les lettres des châssis)
all_tables = ["places", "places_TISSIR", "places_SEFAMAR", "places_V_VLOG"]
for t in all_tables:
    try:
        rows = cursor.execute(f"SELECT id, chassis FROM {t} WHERE chassis IS NOT NULL").fetchall()
        for r_id, r_ch in rows:
            cleaned = clean_chassis(r_ch)
            if cleaned != r_ch:
                cursor.execute(f"UPDATE {t} SET chassis=? WHERE id=?", (cleaned, r_id))
        conn.commit()
    except: pass


# ==========================================
# 🗺️ DEFINITION EXACTE DES COORDONNEES DU PARKING
# ==========================================
spots = []

if park == "ECOMAIL":
    # C15 to C1
    curr_x = 20
    for i in range(15, 0, -1):
        spots.append({"code": f"C{i}", "x": curr_x, "y": 20, "w": 64, "h": 100})
        curr_x += 64
    
    # B64, B65
    curr_y = 500
    for i in range(64, 66):
        spots.append({"code": f"B{i}", "x": 20, "y": curr_y, "w": 100, "h": 40})
        curr_y += 40
    
    # Middle Block B1 to B63
    base_y = 250
    for row in range(21):
        y = base_y + row * 43
        spots.append({"code": f"B{row*3 + 3}", "x": 350, "y": y, "w": 100, "h": 43})
        spots.append({"code": f"B{row*3 + 2}", "x": 450, "y": y, "w": 100, "h": 43})
        spots.append({"code": f"B{row*3 + 1}", "x": 550, "y": y, "w": 100, "h": 43})
    
    # A25 to A1
    curr_y = 200
    for i in range(25, 0, -1):
        spots.append({"code": f"A{i}", "x": 860, "y": curr_y, "w": 120, "h": 36})
        curr_y += 36

    # ==========================
    # Middle Column Spots (D24-D16, W1-W21)
    # ==========================
    m_x = 980
    
    # 3 places vides: D24, D23, D22
    y_box = 20
    for i in range(24, 21, -1):
        spots.append({"code": f"D{i}", "x": m_x, "y": y_box, "w": 150, "h": 33.3})
        y_box += 33.3
        
    # (Autocar Zhong Tong static block is at y=120 to 180)
    
    # D21 to D16
    y_box = 180
    for i in range(21, 15, -1):
        spots.append({"code": f"D{i}", "x": m_x, "y": y_box, "w": 150, "h": 33})
        y_box += 33
        
    # W Block (W21 to W1, numbering from bottom to top)
    w_y = 378
    for i in range(21, 0, -1):
        spots.append({"code": f"W{i}", "x": m_x, "y": w_y, "w": 150, "h": 38.1})
        w_y += 38.1

    # ==========================
    # NEW BLOCK D (Right Side)
    # ==========================
    d_x = 1250
    
    # New D25 to D2 (all divided side-by-side D spots)
    curr_y = 20
    for i in range(24, 1, -2):
        spots.append({"code": f"D{i}", "x": d_x, "y": curr_y, "w": 70, "h": 40})
        spots.append({"code": f"D{i+1}", "x": d_x + 70, "y": curr_y, "w": 70, "h": 40})
        curr_y += 40
        
    # D1
    spots.append({"code": "D1", "x": d_x, "y": 500, "w": 70, "h": 40})
    
    # S35 (Next to D1)
    spots.append({"code": "S35", "x": d_x + 70, "y": 500, "w": 70, "h": 40})
    
    # S34 to S1 (CAMION S 4*2 SITRAK)
    s_y = 540
    for row in range(17):
        left_s = 33 - 2 * row
        right_s = 34 - 2 * row
        spots.append({"code": f"S{left_s}", "x": d_x, "y": s_y, "w": 70, "h": 37})
        spots.append({"code": f"S{right_s}", "x": d_x + 70, "y": s_y, "w": 70, "h": 37})
        s_y += 37
        
    # S36 to S61 (CAMION - 4*2 / 6*4 SITRAK SOLO)
    # Area: x=20, y=1318, width=1370, height=85
    start_x = 20
    start_y = 1318
    s_w = 1370 / 26
    s_h = 85
    s_idx = 61
    for col in range(26):
        spots.append({"code": f"S{s_idx}", "x": start_x + col * s_w, "y": start_y, "w": s_w, "h": s_h})
        s_idx -= 1
        
    # S62 to S68 (CAMION - 4*2 / 6*4 / 3,5 TONNES / ( SOLO ) SITRAK)
    # Area: x=350, y=1180, width=300, height=75
    start_x2 = 350
    start_y2 = 1180
    s_w2 = 300 / 7
    s_h2 = 75
    s_idx2 = 62
    for col in range(7):
        spots.append({"code": f"S{s_idx2}", "x": start_x2 + col * s_w2, "y": start_y2, "w": s_w2, "h": s_h2})
        s_idx2 += 1
else:
    # Generic grid 15 columns x 20 rows (300 places) for other parks
    for row in range(20):
        for col in range(15):
            num = row*15 + col + 1
            spots.append({
                "code": f"P{num}",
                "x": 30 + col*62,
                "y": 50 + row*55,
                "w": 55,
                "h": 40
            })

# S'assurer que toutes les places définies dans 'spots' existent dans la base
existing_codes = {row[0] for row in cursor.execute(f"SELECT code_place FROM {table_name}").fetchall()}
new_spots_to_insert = [s for s in spots if s['code'] not in existing_codes]

if new_spots_to_insert:
    for s in new_spots_to_insert:
        cursor.execute(f"INSERT INTO {table_name} (code_place, status, chassis) VALUES (?, 'libre', NULL)", (s['code'],))
    conn.commit()

# Nettoyer les places obsolètes (qui ne sont plus dans la définition 'spots' du parc actuel)
spots_codes = {s['code'] for s in spots}
obsolete_codes = existing_codes - spots_codes
if obsolete_codes:
    for code in obsolete_codes:
        cursor.execute(f"DELETE FROM {table_name} WHERE code_place=?", (code,))
    conn.commit()


# Si la table était complètement vide au départ, on charge l'Excel
if len(existing_codes) == 0:
    # Charger depuis Excel si possible
    chassis_list = []
    if park == "TISSIR":
        try:
            df = pd.read_excel("ETAT DE TISSIR .xlsx")
            c1 = df.iloc[4:, 2].dropna().astype(str).tolist()
            c2 = df.iloc[4:, 5].dropna().astype(str).tolist()
            chassis_list = c1 + c2
        except: pass
    elif park == "V VLOG":
        try:
            df = pd.read_excel("V VLOG .xlsx")
            # Nettoyer et garder les 6 derniers chiffres
            chassis_list = df.iloc[6:, 1].dropna().astype(str).apply(lambda x: clean_chassis(x)[-6:] if len(clean_chassis(x)) >= 6 else clean_chassis(x)).tolist()
        except: pass
        
    for i, ch in enumerate(chassis_list):
        if i < len(spots):
            code = spots[i]['code']
            ch_clean = clean_chassis(ch)
            cursor.execute(f"UPDATE {table_name} SET status='occupé', chassis=? WHERE code_place=?", (ch_clean, code))
    conn.commit()

# ==========================================
# 🎨 INTERFACE UTILISATEUR
# ==========================================
st.title(f"🚗 Tableau de Bord Digitalisé - {park} Truck")
if park != "ECOMAIL":
    st.info("Le design interactif (carte 2D) de ce parc est une maquette provisoire en attente d'architecture.")

# Charger l'état actuel
db_places = cursor.execute(f"SELECT code_place, status, chassis FROM {table_name}").fetchall()
places_dict = {p[0]: {"status": p[1], "chassis": p[2]} for p in db_places}

col_map, col_panel = st.columns([2.5, 1])

# --- LOGIQUE DU PANNEAU (Droite) ---
with col_panel:
    st.header("🔍 Recherche & Info")
    search_chassis = st.text_input("Entrer le numéro de châssis:")
    
    searched_spot = None
    if search_chassis:
        search_ch_clean = clean_chassis(search_chassis)
        found = False
        all_parks = ["ECOMAIL", "TISSIR", "SEFAMAR", "V VLOG"]
        for p in all_parks:
            t_name = "places" if p == "ECOMAIL" else f"places_{p.replace(' ', '_')}"
            try:
                res = cursor.execute(f"SELECT code_place FROM {t_name} WHERE chassis=?", (search_ch_clean,)).fetchone()
                if res:
                    if p == park:
                        searched_spot = res[0]
                        st.success(f"📍 Véhicule détecté ICI sur la place : **{searched_spot}**")
                    else:
                        st.warning(f"👉 Ce véhicule se trouve dans le parc **{p}** (Place : {res[0]}).")
                    found = True
                    break
            except sqlite3.OperationalError:
                # La table n'a peut-être pas encore été créée si le parc n'a jamais été visité
                pass
        
        if not found:
            st.error("❌ Véhicule introuvable sur aucun parc.")

    st.markdown("---")
    st.subheader("🛠️ Éditer une place")
    
    all_codes = sorted([s["code"] for s in spots], key=lambda x: (x[0], int(x[1:]) if x[1:].isdigit() else 0))
    selected_place = st.selectbox("Sélectionner la place à éditer:", ["-- CHOISIR --"] + all_codes)
    
    if selected_place != "-- CHOISIR --":
        p_info = places_dict.get(selected_place, {"status": "libre", "chassis": None})
        
        st.write(f"### Gestion : {selected_place}")
        
        if p_info["status"] == "libre":
            st.success(f"🟢 État actuel : LIBRE")
            new_ch = st.text_input("Affecter le numéro de châssis:")
            if st.button("Sauvegarder et Assigner", type="primary", use_container_width=True):
                new_ch_clean = clean_chassis(new_ch)
                if new_ch_clean != "":
                    # Vérifier si le châssis existe déjà dans n'importe quel parc
                    chassis_exists = False
                    existing_place = None
                    existing_park = None
                    all_parks = ["ECOMAIL", "TISSIR", "SEFAMAR", "V VLOG"]
                    for p in all_parks:
                        t_name = "places" if p == "ECOMAIL" else f"places_{p.replace(' ', '_')}"
                        try:
                            res = cursor.execute(f"SELECT code_place FROM {t_name} WHERE chassis=?", (new_ch_clean,)).fetchone()
                            if res:
                                chassis_exists = True
                                existing_place = res[0]
                                existing_park = p
                                break
                        except sqlite3.OperationalError:
                            pass
                    
                    if chassis_exists:
                        if existing_park == park:
                            st.error(f"❌ Impossible : Ce numéro de châssis est déjà réservé dans la place **{existing_place}**. Veuillez d'abord supprimer l'ancienne affectation.")
                        else:
                            st.error(f"❌ Impossible : Ce numéro de châssis est déjà réservé dans le parc **{existing_park}** (Place **{existing_place}**). Veuillez d'abord supprimer l'ancienne affectation.")
                    else:
                        cursor.execute(f"UPDATE {table_name} SET status='occupé', chassis=? WHERE code_place=?", (new_ch_clean, selected_place))
                        cursor.execute("INSERT INTO history (username, park_name, action, code_place, new_chassis) VALUES (?, ?, ?, ?, ?)", (st.session_state.username, park, "Assignation", selected_place, new_ch_clean))
                        conn.commit()
                        supabase_upsert(table_name, {"code_place": selected_place, "status": "occupé", "chassis": new_ch_clean})
                        supabase_insert("history", {
                            "username": st.session_state.username,
                            "park_name": park,
                            "action": "Assignation",
                            "code_place": selected_place,
                            "new_chassis": new_ch_clean
                        })
                        st.rerun()
                else:
                    st.warning("Veuillez entrer un numéro de châssis valide.")
        else:
            curr_ch = p_info["chassis"]
            st.error(f"🔴 État actuel : OCCUPÉ par `{curr_ch}`")
            if st.button("Libérer cette place", use_container_width=True):
                cursor.execute(f"UPDATE {table_name} SET status='libre', chassis=NULL WHERE code_place=?", (selected_place,))
                cursor.execute("INSERT INTO history (username, park_name, action, code_place, old_chassis) VALUES (?, ?, ?, ?, ?)", (st.session_state.username, park, "Libération", selected_place, curr_ch))
                conn.commit()
                supabase_upsert(table_name, {"code_place": selected_place, "status": "libre", "chassis": None})
                supabase_insert("history", {
                    "username": st.session_state.username,
                    "park_name": park,
                    "action": "Libération",
                    "code_place": selected_place,
                    "old_chassis": curr_ch
                })
                st.rerun()
                
    st.markdown("---")
    st.subheader("🔄 Transférer un véhicule")
    t_chassis = st.text_input("Châssis à transférer:")
    
    all_parks_list = ["ECOMAIL", "TISSIR", "SEFAMAR", "V VLOG"]
    t_park_dest = st.selectbox("Vers le parc:", all_parks_list, index=all_parks_list.index(park))
    
    t_table_dest = "places" if t_park_dest == "ECOMAIL" else f"places_{t_park_dest.replace(' ', '_')}"
    free_places_dest = [r[0] for r in cursor.execute(f"SELECT code_place FROM {t_table_dest} WHERE status='libre'").fetchall()]
    
    t_dest = st.selectbox("Vers la place:", ["-- CHOISIR --"] + sorted(free_places_dest))
    
    if st.button("Effectuer le transfert", use_container_width=True):
        t_ch_clean = clean_chassis(t_chassis)
        if t_ch_clean and t_dest != "-- CHOISIR --":
            chassis_exists = False
            existing_place = None
            existing_tname = None
            
            for p in all_parks_list:
                t_name_check = "places" if p == "ECOMAIL" else f"places_{p.replace(' ', '_')}"
                try:
                    res = cursor.execute(f"SELECT code_place FROM {t_name_check} WHERE chassis=?", (t_ch_clean,)).fetchone()
                    if res:
                        chassis_exists = True
                        existing_place = res[0]
                        existing_tname = t_name_check
                        break
                except sqlite3.OperationalError:
                    pass
            
            if chassis_exists:
                # Libérer l'ancienne place
                cursor.execute(f"UPDATE {existing_tname} SET status='libre', chassis=NULL WHERE code_place=?", (existing_place,))
                # Occuper la nouvelle place dans le parc de destination
                cursor.execute(f"UPDATE {t_table_dest} SET status='occupé', chassis=? WHERE code_place=?", (t_ch_clean, t_dest))
                # Enregistrer l'historique
                cursor.execute("INSERT INTO history (username, park_name, action, code_place, old_chassis, new_chassis) VALUES (?, ?, ?, ?, ?, ?)", (st.session_state.username, t_park_dest, f"Transfert (depuis {existing_place})", t_dest, t_ch_clean, t_ch_clean))
                conn.commit()
                supabase_upsert(existing_tname, {"code_place": existing_place, "status": "libre", "chassis": None})
                supabase_upsert(t_table_dest, {"code_place": t_dest, "status": "occupé", "chassis": t_ch_clean})
                supabase_insert("history", {
                    "username": st.session_state.username,
                    "park_name": t_park_dest,
                    "action": f"Transfert (depuis {existing_place})",
                    "code_place": t_dest,
                    "old_chassis": t_ch_clean,
                    "new_chassis": t_ch_clean
                })
                st.success(f"✅ Transfert réussi vers {t_park_dest} ({t_dest}) !")
                st.rerun()
            else:
                st.error("❌ Ce châssis n'est pas enregistré. Utilisez 'Éditer une place' pour l'ajouter.")

        else:
            st.warning("Veuillez remplir tous les champs.")

    st.markdown("---")
    st.subheader("📊 Statistiques")
    total_spots = len(all_codes)
    occupied = sum(1 for p in db_places if p[1] == 'occupé')
    free = total_spots - occupied
    
    colA, colB = st.columns(2)
    colA.metric(label="🟢 LIBRES", value=free)
    colB.metric(label="🔴 OCCUPÉES", value=occupied)

# --- GENERATION SVG - CARTE VISUELLE (Gauche) ---
with col_map:
    st.header(f"🗺️ Vue 2D Interactive - {park}")
    
    show_chassis = st.toggle("🔍 Afficher les numéros de châssis sur la carte", value=False)
    
    svg_elements = []
    
    if park == "ECOMAIL":
        # Cadre extérieur (qui regroupe tout)
        svg_elements.append('<rect x="-45" y="-45" width="1435" height="1463" fill="none" stroke="#212529" stroke-width="6" />')

        # ================================
        # BLUE ROAD (ROUTE)
        # ================================
        # Segment du haut (au dessus de la rangée C)
        svg_elements.append('<rect x="-45" y="-45" width="1435" height="65" fill="#b0cbf4" />')
        
        # Segment gauche (à gauche de C15 et des camions militaires)
        svg_elements.append('<rect x="-45" y="-45" width="65" height="1463" fill="#b0cbf4" />')
        
        # Route continue tout en bas pour la circulation
        svg_elements.append('<rect x="20" y="1255" width="630" height="63" fill="#b0cbf4" />')
        svg_elements.append('<rect x="650" y="1180" width="740" height="138" fill="#b0cbf4" stroke="#212529" stroke-width="2" />')
        
        # Dessiner l'entré pour ECOMAIL
        svg_elements.append('<rect x="665" y="1160" width="160" height="40" fill="#f8cbad" stroke="#212529" stroke-width="2" />')
        svg_elements.append('<text x="745" y="1185" fill="#212529" font-size="18" font-family="sans-serif" font-weight="bold" text-anchor="middle">Entré 2</text>')

        # Entrée Haut Droite (Entré 1) au niveau de D25
        svg_elements.append('<rect x="1390" y="-45" width="40" height="65" fill="#f8cbad" stroke="#212529" stroke-width="2" />')
        svg_elements.append('<text x="1415" y="-12" fill="#212529" font-size="14" font-family="sans-serif" font-weight="bold" text-anchor="middle" transform="rotate(90 1415 -12)">Entré 1</text>')

        # Entrée Bas Droite (placée à côté de la route bleue et du bloc SITRAK)
        svg_elements.append('<rect x="1390" y="1180" width="40" height="240" fill="#f8cbad" stroke="#212529" stroke-width="2" />')
        svg_elements.append('<text x="1415" y="1300" fill="#212529" font-size="18" font-family="sans-serif" font-weight="bold" text-anchor="middle" transform="rotate(90 1415 1300)">Entré 3</text>')

        # ================================
        # ZONES STATIQUES DE COULEUR
        # ================================
        # Zones Camions Militaire (Ajustées à l'image)
        # Un grand bloc vertical pour la zone militaire gauche (y=120 à y=1180)
        svg_elements.append('<rect x="20" y="120" width="192" height="1060" fill="#c2b280" stroke="#212529" stroke-width="2" />')
        svg_elements.append('<text x="116" y="310" fill="#212529" font-size="12" font-family="sans-serif" font-weight="bold" text-anchor="middle">CAMIONS</text>')
        svg_elements.append('<text x="116" y="325" fill="#212529" font-size="12" font-family="sans-serif" font-weight="bold" text-anchor="middle">MILITAIRE</text>')

        svg_elements.append('<text x="116" y="880" fill="#212529" font-size="12" font-family="sans-serif" font-weight="bold" text-anchor="middle">CAMIONS</text>')
        svg_elements.append('<text x="116" y="895" fill="#212529" font-size="12" font-family="sans-serif" font-weight="bold" text-anchor="middle">MILITAIRE</text>')

        # Zone horizontale tout en bas (Largeur ajustée jusqu'à la colonne B63)
        svg_elements.append('<rect x="20" y="1180" width="330" height="75" fill="#c2b280" stroke="#212529" stroke-width="2" />')
        svg_elements.append('<text x="185" y="1225" fill="#212529" font-size="14" font-family="sans-serif" font-weight="bold" text-anchor="middle">CAMIONS MILITAIRE</text>')

        # (La zone Orange est maintenant gérée dynamiquement dans spots S62 à S68)

        # (La zone Orange en bas à droite est maintenant gérée dynamiquement dans spots S36 à S61)

        m_x = 980 # Middle column
        
        # Le mur de séparation (Ligne noire épaisse)
        svg_elements.append(f'<line x1="{m_x}" y1="20" x2="{m_x}" y2="1180" stroke="#212529" stroke-width="6" />')
        
        # Mur horizontal entre D24 et 4 CAMIONS 3,5 (x=1130 à x=1250 à y=20)
        svg_elements.append('<line x1="1130" y1="20" x2="1250" y2="20" stroke="#212529" stroke-width="6" />')
        
        # (L'espace 4 CAMIONS est maintenant dynamique: D24, D23, D22)
        
        # AUTOCAR ZHONG TONG
        svg_elements.append(f'<rect x="{m_x}" y="120" width="150" height="60" fill="#d9d9d9" stroke="#212529" stroke-width="2" />')
        svg_elements.append(f'<text x="{m_x + 75}" y="145" fill="#212529" font-size="12" font-family="sans-serif" font-weight="bold" text-anchor="middle">AUTOCAR</text>')
        svg_elements.append(f'<text x="{m_x + 75}" y="160" fill="#212529" font-size="12" font-family="sans-serif" font-weight="bold" text-anchor="middle">ZHONG TONG</text>')

        # (Le bloc vert WIELTON est maintenant géré dynamiquement dans spots avec W1 à W21)

        # D column zones
        d_x = 1250
        # (L'espace 8*4 est maintenant géré dynamiquement dans spots)

        # (L'espace vide à côté de D1 est maintenant la place S35)
        
        # Effacer la ligne du cadre en bas pour créer le passage ouvert
        svg_elements.append('<line x1="1132" y1="1180" x2="1248" y2="1180" stroke="#f8f9fa" stroke-width="8" />')
    else:
        # Cadre générique
        svg_elements.append('<rect x="20" y="20" width="960" height="1160" fill="none" stroke="#212529" stroke-width="6" />')
    
    # Dessiner les emplacements
    for s in spots:
        code = s["code"]
        info = places_dict.get(code, {"status": "libre"})
        
        bg_color = "#198754" if info["status"] == "libre" else "#dc3545"
        stroke = "#212529"
        stroke_width = "2"
        
        # Mettre en évidence si recherché
        if searched_spot and code == searched_spot:
            stroke = "#0dcaf0" # Cyan for highlight
            stroke_width = "4"
            bg_color = "#fd7e14" # Orange
            
        rect = f'<rect x="{s["x"]}" y="{s["y"]}" width="{s["w"]}" height="{s["h"]}" fill="{bg_color}" stroke="{stroke}" stroke-width="{stroke_width}"><title>Place: {code} | Status: {info["status"]} {(" | Chassis: " + info["chassis"]) if info["chassis"] else ""}</title></rect>'
        
        txt_x = s["x"] + s["w"]/2
        txt_y = s["y"] + s["h"]/2 + 5
        
        display_text = code
        font_size = "14"
        text_length_attr = ""
        
        if show_chassis and info.get("chassis"):
            display_text = str(info["chassis"])
            font_size = "10"
            # Si le texte est trop long pour la boîte (approx 6px par caractère), on le compresse
            if len(display_text) * 6 > s["w"] - 4:
                text_length_attr = f' textLength="{s["w"] - 4}" lengthAdjust="spacingAndGlyphs"'
                
        text = f'<text x="{txt_x}" y="{txt_y}" fill="white" font-size="{font_size}" font-family="sans-serif" font-weight="bold" text-anchor="middle"{text_length_attr}>{display_text}</text>'
            
        svg_elements.append(rect)
        svg_elements.append(text)
        
    svg_str = f"""
    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 12px; border: 1px solid #dee2e6; box-shadow: 0 4px 10px rgba(0,0,0,0.05); width: 100%; height: 800px; overflow: hidden; position: relative;">
        <svg id="parking-map" viewBox="-45 -45 1495 1370" style="width: 100%; height: 100%; background-color: #f8f9fa;">
            {" ".join(svg_elements)}
        </svg>
        <script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
        <script>
            window.onload = function() {{
                var svgElement = document.getElementById('parking-map');
                if(svgElement) {{
                    svgPanZoom(svgElement, {{
                      zoomEnabled: true,
                      controlIconsEnabled: true,
                      fit: true,
                      center: true,
                      minZoom: 0.5,
                      maxZoom: 5,
                      zoomScaleSensitivity: 0.2
                    }});
                }}
            }};
        </script>
    </div>
    """
    
    st.components.v1.html(svg_str, height=850, scrolling=False)