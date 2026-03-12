from flask import Flask, render_template, request, Blueprint

import os
import pandas as pd

bp = Blueprint('at', __name__, template_folder='templates')

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def cargar_archivo_flexible(ruta):
    try:
        return pd.read_excel(ruta, engine='openpyxl')
    except:
        return pd.read_csv(ruta, encoding='latin1', sep=None, engine='python')

def obtener_catalogo_maestro():
    ruta_catalogo = "claves.csv"
    if os.path.exists(ruta_catalogo):
        try:
            df_cat = pd.read_csv(ruta_catalogo, header=None, names=['Clave', 'Descripcion'], dtype=str, encoding='latin1')
        except:
            df_cat = pd.read_csv(ruta_catalogo, header=None, names=['Clave', 'Descripcion'], dtype=str, encoding='utf-8')
        df_cat['Clave'] = df_cat['Clave'].str.strip()
        df_cat['Descripcion'] = df_cat['Descripcion'].str.strip().fillna("SIN DESCRIPCIÓN")
        return df_cat.set_index('Clave')['Descripcion'].to_dict()
    return {}

@bp.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if 'archivo' not in request.files: return "No hay archivo"
        archivo = request.files["archivo"]
        if archivo.filename == '': return "No seleccionado"
        
        ruta = os.path.join(app.config['UPLOAD_FOLDER'], archivo.filename)
        archivo.save(ruta)

        try:
            df = cargar_archivo_flexible(ruta)
            df.columns = [c.strip() for c in df.columns]

            # --- CONFIGURACIÓN DE COLUMNAS ---
            COL_ID = next((c for c in df.columns if 'ID' == c.upper() or 'IDENTIFICADOR' in c.upper()), None)
            COL_FOLIO = next((c for c in df.columns if 'FOLIO' in c.upper()), 'Folio')
            COL_FECHA = next((c for c in df.columns if 'FECHA' in c.upper() and 'SURTIMIENTO' in c.upper()), 'Fecha Surtimiento')
            COL_CLAVE = next((c for c in df.columns if 'CLAVE' in c.upper() and 'SECTOR' in c.upper()), 'Clave Sector Salud')
            COL_DESC = next((c for c in df.columns if 'DESCRIPCI' in c.upper()), 'DESCRIPCIÓN')
            COL_EXPEDIDA = next((c for c in df.columns if 'CANTIDAD' in c.upper() and 'EXPEDIDA' in c.upper()), 'Cantidad Expedida')
            COL_RECETADA = next((c for c in df.columns if 'CANTIDAD' in c.upper() and 'RECETADA' in c.upper()), 'Cantidad Recetada')

            if not COL_ID:
                df['ID_SISTEMA'] = range(len(df))
                COL_ID = 'ID_SISTEMA'

            # --- LIMPIEZA ---
            df[COL_FECHA] = pd.to_datetime(df[COL_FECHA], errors='coerce')
            df = df.dropna(subset=[COL_FECHA, COL_FOLIO])
            df['Dia'] = df[COL_FECHA].dt.day.astype(int)
            df[COL_EXPEDIDA] = pd.to_numeric(df[COL_EXPEDIDA], errors='coerce').fillna(0)
            df[COL_RECETADA] = pd.to_numeric(df[COL_RECETADA], errors='coerce').fillna(0)
            df['EXP_LIMPIA'] = df[COL_EXPEDIDA].apply(lambda x: x if x > 0 else 0)
            
            dias_eje = sorted(df['Dia'].unique().tolist())

            # --- 1. RESUMEN SUPERIOR ---
            resumen_superior = []
            for dia in dias_eje:
                df_dia = df[df['Dia'] == dia]
                folios_dia = df_dia[COL_FOLIO].unique()
                r_surt, r_parc, r_nega = 0, 0, 0
                for f in folios_dia:
                    df_f = df_dia[df_dia[COL_FOLIO] == f]
                    t_surtido = (df_f[COL_EXPEDIDA] > 0).any()
                    t_negado = (df_f[COL_EXPEDIDA] == 0).any()
                    if t_surtido and not t_negado: r_surt += 1
                    elif t_surtido and t_negado: r_parc += 1
                    else: r_nega += 1
                
                resumen_superior.append({
                    'dia': dia, 
                    'r_surtidas': r_surt, 
                    'r_parciales': r_parc, 
                    'r_negadas': r_nega,
                    'p_surtidas': int(df_dia['EXP_LIMPIA'].sum()),
                    'p_negadas': int(df_dia[df_dia[COL_EXPEDIDA] == 0][COL_RECETADA].sum()),
                    'c_surtidas': df_dia[df_dia[COL_EXPEDIDA] > 0][COL_CLAVE].nunique(),
                    'c_negadas': df_dia[df_dia[COL_EXPEDIDA] == 0][COL_CLAVE].nunique()
                })

                        # --- 2. MATRICES (OC99) ---
            
            # 1. Identificar colisiones en el catálogo para saber qué claves dejar a 15 caracteres
            catalogo_crudo = obtener_catalogo_maestro()
            if not catalogo_crudo:
                # Si no hay catálogo, generamos uno base de 12 caracteres desde el DF
                catalogo = df[[COL_CLAVE, COL_DESC]].drop_duplicates(COL_CLAVE).set_index(COL_CLAVE)[COL_DESC].to_dict()
            else:
                # Buscamos bases de 12 que se repiten (ej. .00 y .02)
                import collections
                claves_lista = [str(k).strip() for k in catalogo_crudo.keys()]
                conteo_bases = collections.Counter([k[:12] for k in claves_lista])
                
                # Definimos la función de normalización según tu sugerencia
                def normalizar_hibrido(c):
                    c_str = str(c).strip()
                    base_12 = c_str[:12]
                    # Si la base tiene colisiones, respetamos los 15 caracteres, si no, a 12
                    return c_str[:15] if conteo_bases[base_12] > 1 else base_12
    
                # Aplicamos la normalización al DataFrame y creamos el catálogo final
                df[COL_CLAVE] = df[COL_CLAVE].apply(normalizar_hibrido)
                catalogo = {normalizar_hibrido(k): v for k, v in catalogo_crudo.items()}
    
            # Ordenamos para que la descripción más completa quede arriba
            df = df.sort_values(by=[COL_CLAVE, COL_DESC], ascending=[True, False])
    
            # 2. Generación de Matrices y Reportes (Usando las 330 claves)
            claves_orden = sorted(list(catalogo.keys()))
    
            # Surtidos: aggfunc='sum' consolidará las capturas de .01, .02 en la base .00 SOLO si no son colisiones
            m_surt = df[df[COL_EXPEDIDA] > 0].pivot_table(index=COL_CLAVE, columns='Dia', values=COL_EXPEDIDA, aggfunc='sum').reindex(claves_orden).fillna(0)
            reporte_surtido = [{'clave': c, 'descripcion': catalogo.get(c, "S/D"), 'dias': m_surt.loc[c].to_dict(), 'total': int(m_surt.loc[c].sum())} for c in claves_orden]
    
            # Negados
            m_neg = df[df[COL_EXPEDIDA] == 0].pivot_table(index=COL_CLAVE, columns='Dia', values=COL_RECETADA, aggfunc='sum').reindex(claves_orden).fillna(0)
            reporte_negados = [{'clave': c, 'descripcion': catalogo.get(c, "S/D"), 'dias': m_neg.loc[c].to_dict(), 'total': int(m_neg.loc[c].sum())} for c in claves_orden]
    
            # --- 3. FOLIOS, DUPLICADOS Y EXCEDIDOS ---
            listado_folios = []
            for dia in dias_eje:
                df_dia = df[df['Dia'] == dia]
                f_det = []
                for f in sorted(df_dia[COL_FOLIO].unique()):
                    df_f = df_dia[df_dia[COL_FOLIO] == f]
                    f_det.append({
                        'numero': f, 
                        'es_negado': not (df_f[COL_EXPEDIDA] > 0).any(), 
                        'es_parcial': (df_f[COL_EXPEDIDA] > 0).any() and (df_f[COL_EXPEDIDA] == 0).any()
                    })
                listado_folios.append({'dia': dia, 'folios': f_det, 'cantidad': len(f_det)})
    
            # Duplicados (Usa la clave normalizada híbrida)
            dup_df = df.groupby(COL_FOLIO).agg({COL_ID: 'nunique', COL_FECHA: 'min'}).reset_index()
            listado_duplicados = [
                {
                    'dia': r[COL_FECHA].day,
                    'folio': r[COL_FOLIO], 
                    'total': df[df[COL_FOLIO] == r[COL_FOLIO]][COL_ID].nunique(), 
                    'fechas': df[df[COL_FOLIO] == r[COL_FOLIO]][COL_FECHA].dt.strftime('%d/%m/%Y').unique().tolist()
                } for _, r in dup_df[dup_df[COL_ID] > 1].iterrows()
            ]
    
            # Excedidos (Usa la clave normalizada híbrida)
            exc_df = df.groupby(COL_FOLIO).agg({COL_CLAVE: 'nunique', COL_FECHA: 'min'}).reset_index()
            listado_excedidos = [
                {
                    'dia': r[COL_FECHA].day,
                    'fecha': r[COL_FECHA].strftime('%d/%m/%Y'), 
                    'folio': r[COL_FOLIO], 
                    'cantidad_claves': r[COL_CLAVE], 
                    'detalles': df[df[COL_FOLIO] == r[COL_FOLIO]][COL_CLAVE].unique().tolist()
                } for _, r in exc_df[exc_df[COL_CLAVE] > 3].iterrows()
            ]


            # --- 4. SIGNOS NEGATIVOS Y DETALLE MODAL ---
            df_negativos = df[df[COL_EXPEDIDA] < 0]
            listado_signos_negativos = [{'dia': d, 'detalles': df_negativos[df_negativos['Dia'] == d][[COL_FOLIO, COL_CLAVE, COL_EXPEDIDA]].to_dict(orient='records')} for d in dias_eje if not df_negativos[df_negativos['Dia'] == d].empty]

            detalle_folios_dict = {}
            for folio in df[COL_FOLIO].unique():
                df_f = df[df[COL_FOLIO] == folio]
                detalle_folios_dict[str(folio)] = df_f.rename(columns={
                    COL_CLAVE: 'Clave',
                    COL_DESC: 'Descripcion',
                    COL_RECETADA: 'Recetada',
                    COL_EXPEDIDA: 'Surtida'
                })[['Clave', 'Descripcion', 'Recetada', 'Surtida']].to_dict(orient='records')

            return render_template("resultado.html", 
                                   resumen=resumen_superior, 
                                   reporte_surtido=reporte_surtido, 
                                   reporte_negados=reporte_negados, 
                                   listado_folios=listado_folios, 
                                   listado_duplicados=listado_duplicados, 
                                   listado_excedidos=listado_excedidos, 
                                   listado_signos_negativos=listado_signos_negativos,
                                   detalle_folios=detalle_folios_dict,
                                   dias=dias_eje)

        except Exception as e:
            return f"Error: {str(e)}"
    return render_template("index.html")



