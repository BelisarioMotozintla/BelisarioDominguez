
from flask import Flask, render_template, request, Blueprint,jsonify
import os
import pandas as pd
import json
from app.utils.helpers import roles_required
from app.utils.helpers import usuarios_con_rol_requerido
from app import db
from app.models import BloqueReceta, AsignacionReceta, Usuario,Roles, RecetaMedica,InventarioFarmacia,Medicamento,DetalleReceta,Diagnostico,SalidaFarmacia
from app.utils.helpers import roles_required
from flask_login import current_user


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
    # 1. Obtiene la ruta de la carpeta donde está este script (app/at/)
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    # 2. Une esa carpeta con el nombre del archivo
    ruta_catalogo = os.path.join(directorio_actual, "claves.csv")
    
    print(f"DEBUG RENDER: Buscando catálogo en {ruta_catalogo}")

    if os.path.exists(ruta_catalogo):
        try:
            df_cat = pd.read_csv(
                ruta_catalogo,   
                header=None, 
                names=['Clave', 'Descripcion'], 
                dtype=str, 
                encoding='latin1',
                engine='python',
                on_bad_lines='skip' 
            )
            # Limpieza para que coincidan los 330 registros
            df_cat['Clave'] = df_cat['Clave'].str.replace(r'\r', '', regex=True).str.strip()
            df_cat['Descripcion'] = df_cat['Descripcion'].str.replace(r'\r', '', regex=True).str.strip().fillna("SIN DESCRIPCIÓN")
            
            dicc = df_cat.set_index('Clave')['Descripcion'].to_dict()
            print(f"ÉXITO: Se cargaron {len(dicc)} claves del maestro")
            return dicc
        except Exception as e:
            print(f"Error leyendo el archivo: {e}")
            return {}
            
    print("ALERTA: El archivo físico NO está en esa ruta")
    return {}


@bp.route("/auditoria", methods=["GET", "POST"])
@roles_required([ 'UsuarioAdministrativo', 'Administrador'])
def auditoria():
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
            catalogo_crudo = obtener_catalogo_maestro()
            catalogo_crudo = {str(k).strip().replace('\r', ''): v for k, v in catalogo_crudo.items()}
            if not catalogo_crudo:
                print("ALERTA: No se encontró claves.csv en Render, usando datos de la receta")
                catalogo = df[[COL_CLAVE, COL_DESC]].drop_duplicates(COL_CLAVE).set_index(COL_CLAVE)[COL_DESC].to_dict()
            else:
                import collections
                claves_lista = [str(k).strip() for k in catalogo_crudo.keys()]
                conteo_bases = collections.Counter([k[:12] for k in claves_lista])
                
                def normalizar_hibrido(c):
                    c_str = str(c).strip()
                    base_12 = c_str[:12]
                    return c_str[:15] if conteo_bases[base_12] > 1 else base_12
                 
                df[COL_CLAVE] = df[COL_CLAVE].astype(str).str.strip().str.replace('\r', '', regex=True)
                df[COL_CLAVE] = df[COL_CLAVE].apply(normalizar_hibrido)
                catalogo = {normalizar_hibrido(k): v for k, v in catalogo_crudo.items()}
    
            df = df.sort_values(by=[COL_CLAVE, COL_DESC], ascending=[True, False])
            
            # ==========================================
            # DATAFRAME LIMPIO PARA DETALLE OC99
            # ==========================================
            df_detalle = df.copy()
            df_detalle = df_detalle.drop_duplicates(
                subset=[COL_FOLIO, COL_CLAVE],
                keep='first'
            )

            folios_validos = (
                df_detalle.groupby(COL_FOLIO)[COL_CLAVE]
                .nunique()
            )
            folios_validos = folios_validos[folios_validos <= 3].index.tolist()
            df_detalle = df_detalle[df_detalle[COL_FOLIO].isin(folios_validos)]
            # 2. Generación de Matrices y Reportes (Usando las 330 claves)
            claves_orden = sorted(list(catalogo.keys()))
    
            m_surt = df[df[COL_EXPEDIDA] > 0].pivot_table(index=COL_CLAVE, columns='Dia', values=COL_EXPEDIDA, aggfunc='sum').reindex(claves_orden).fillna(0)
            reporte_surtido = [{'clave': c, 'descripcion': catalogo.get(c, "S/D"), 'dias': m_surt.loc[c].to_dict(), 'total': int(m_surt.loc[c].sum())} for c in claves_orden]
    
            m_neg = df[df[COL_EXPEDIDA] == 0].pivot_table(index=COL_CLAVE, columns='Dia', values=COL_RECETADA, aggfunc='sum').reindex(claves_orden).fillna(0)
            reporte_negados = [{'clave': c, 'descripcion': catalogo.get(c, "S/D"), 'dias': m_neg.loc[c].to_dict(), 'total': int(m_neg.loc[c].sum())} for c in claves_orden]
    
            # --- 3. FOLIOS, DUPLICADOS Y EXCEDIDOS ---
            listado_folios = []
            for dia in dias_eje:
                df_dia = df_detalle[df_detalle['Dia'] == dia]
                f_det = []
                for f in sorted(df_dia[COL_FOLIO].unique()):
                    df_f = df_dia[df_dia[COL_FOLIO] == f]
                    
                    # 🌟 FORZAMOS LA CONVERSIÓN A BOOL NATIVO CON bool() 🌟
                    es_negado_nativo = bool(not (df_f[COL_EXPEDIDA] > 0).any())
                    es_parcial_nativo = bool((df_f[COL_EXPEDIDA] > 0).any() and (df_f[COL_EXPEDIDA] == 0).any())
                    
                    f_det.append({
                        'numero': f, 
                        'es_negado': es_negado_nativo, 
                        'es_parcial': es_parcial_nativo
                    })
                listado_folios.append({'dia': dia, 'folios': f_det, 'cantidad': len(f_det)})
    
            # Duplicados
            dup_df = df.groupby(COL_FOLIO).agg({COL_ID: 'nunique', COL_FECHA: 'max'}).reset_index()
            listado_duplicados = [
                {
                    'dia': r[COL_FECHA].day,
                    'folio': r[COL_FOLIO], 
                    'total': df[df[COL_FOLIO] == r[COL_FOLIO]][COL_ID].nunique(), 
                    'fechas': df[df[COL_FOLIO] == r[COL_FOLIO]][COL_FECHA].dt.strftime('%d/%m/%Y').unique().tolist()
                } for _, r in dup_df[dup_df[COL_ID] > 1].iterrows()
            ]
    
            # Excedidos
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
            for folio in sorted(df_detalle[COL_FOLIO].unique()):
                df_f = df_detalle[df_detalle[COL_FOLIO] == folio]
                detalle_folios_dict[str(folio)] = (
                    df_f.rename(columns={
                        COL_CLAVE: 'Clave',
                        COL_DESC: 'Descripcion',
                        COL_RECETADA: 'Recetada',
                        COL_EXPEDIDA: 'Surtida'
                    })
                    [['Clave', 'Descripcion', 'Recetada', 'Surtida']]
                    .to_dict(orient='records')
                )
			
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

#_______________+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

import time
from datetime import datetime

from flask import jsonify, request
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError, OperationalError


def clave_base(clave):
    """
    Convierte:

        010.000.5186.00
        010.000.5186.01
        010.000.5186.02

    en

        010.000.5186
    """

    clave = str(clave).strip()

    partes = clave.split(".")

    if len(partes) >= 3:
        return ".".join(partes[:3])

    return clave
#++++++++++++++++++++++++

import time
import collections
from datetime import datetime

from flask import jsonify, request
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError, OperationalError

@bp.route("/guardar_dia", methods=["POST"])
@roles_required(["UsuarioAdministrativo", "Administrador"])
def guardar_dia_local():

    try:

        print("\n" + "=" * 70)
        print(">>> INICIANDO GUARDAR_DIA")
        print("=" * 70)

        payload = request.get_json() or {}

        dia_seleccionado = payload.get("dia")
        recetas_inyectadas = payload.get("recetas", {})

        print(f">>> DIA: {dia_seleccionado}")
        print(f">>> FOLIOS RECIBIDOS: {len(recetas_inyectadas)}")

        if not recetas_inyectadas:
            return jsonify({
                "status": "error",
                "message": "No se encontraron folios."
            }), 400

        # ============================================================
        # 1. NORMALIZAR FOLIOS
        # ============================================================

        recetas_normalizadas = {}

        for folio, medicamentos in recetas_inyectadas.items():

            folio = str(folio).strip()

            if folio:
                recetas_normalizadas[folio] = medicamentos

        folios_enviados = list(recetas_normalizadas.keys())

        # ============================================================
        # 2. BUSCAR FOLIOS YA EXISTENTES
        # ============================================================

        folios_existentes = {
            str(folio).strip()
            for (folio,) in (
                db.session.query(RecetaMedica.folio)
                .filter(RecetaMedica.folio.in_(folios_enviados))
                .all()
            )
        }

        folios_nuevos = {
            folio: medicamentos
            for folio, medicamentos in recetas_normalizadas.items()
            if folio not in folios_existentes
        }

        print(f">>> FOLIOS YA EXISTENTES: {len(folios_existentes)}")
        print(f">>> FOLIOS NUEVOS: {len(folios_nuevos)}")

        if not folios_nuevos:

            return jsonify({
                "status": "success",
                "guardados": 0,
                "omitidos": len(folios_existentes),
                "folios_omitidos": sorted(folios_existentes),
                "message": "Todos los folios ya estaban registrados."
            }), 200

        # ============================================================
        # 3. CARGAR MEDICAMENTOS DE LA BD
        #
        # claves.csv es espejo de Medicamento.
        #
        # Aquí NO usamos directamente una clave de 12 caracteres
        # como identificador final.
        #
        # Se construye una tabla que permite encontrar:
        #
        # 010.000.5186
        # 010.000.5186.00
        # 010.000.5186.01
        # 010.000.5186.02
        #
        # según lo que exista realmente en BD.
        # ============================================================

        medicamentos_db = (
            db.session.query(Medicamento, InventarioFarmacia)
            .outerjoin(
                InventarioFarmacia,
                InventarioFarmacia.id_medicamento ==
                Medicamento.id_medicamento
            )
            .all()
        )

        print(f">>> TOTAL MEDICAMENTOS CARGADOS: {len(medicamentos_db)}")

        # ============================================================
        # 4. CONSTRUIR ÍNDICES DE CLAVES
        # ============================================================

        indice_clave_exacta = {}
        indice_clave_base = {}

        for medicamento, inventario in medicamentos_db:

            clave_db = str(medicamento.clave or "").strip()

            if not clave_db:
                continue

            # Limpieza
            clave_db = clave_db.replace("\r", "").replace("\n", "").strip()

            # Coincidencia exacta
            indice_clave_exacta[clave_db] = {
                "medicamento": medicamento,
                "inventario": inventario
            }

            # Base:
            #
            # 010.000.5186.00 -> 010.000.5186
            # 010.000.5186.01 -> 010.000.5186
            # 010.000.5186.02 -> 010.000.5186
            #
            partes = clave_db.split(".")

            if len(partes) >= 3:

                clave_base = ".".join(partes[:3])

                indice_clave_base.setdefault(
                    clave_base,
                    []
                ).append({
                    "clave": clave_db,
                    "medicamento": medicamento,
                    "inventario": inventario
                })

        # ============================================================
        # 5. FUNCIÓN PARA ENCONTRAR EL MEDICAMENTO
        # ============================================================

        def buscar_medicamento(clave_receta):

            clave_receta = str(clave_receta or "").strip()

            clave_receta = (
                clave_receta
                .replace("\r", "")
                .replace("\n", "")
                .strip()
            )

            if not clave_receta:
                return None

            # --------------------------------------------------------
            # PRIMERA OPCIÓN:
            # coincidencia exacta
            # --------------------------------------------------------

            encontrado = indice_clave_exacta.get(clave_receta)

            if encontrado:
                return encontrado

            # --------------------------------------------------------
            # SEGUNDA OPCIÓN:
            # coincidencia por clave base
            #
            # Ejemplo:
            #
            # SAI:
            # 010.000.5186
            #
            # BD:
            # 010.000.5186.00
            #
            # --------------------------------------------------------

            partes = clave_receta.split(".")

            if len(partes) >= 3:

                clave_base = ".".join(partes[:3])

                candidatos = indice_clave_base.get(
                    clave_base,
                    []
                )

                if len(candidatos) == 1:
                    return candidatos[0]

                # ----------------------------------------------------
                # Si hay varias variantes:
                #
                # .00
                # .01
                # .02
                #
                # Primero intentamos .00 porque es la representación
                # estándar cuando SAI solamente entrega la base.
                # ----------------------------------------------------

                for candidato in candidatos:

                    clave_candidato = candidato["clave"]

                    if clave_candidato.endswith(".00"):
                        return candidato

                # ----------------------------------------------------
                # Si no existe .00 y solo hay un candidato válido,
                # utilizarlo.
                # ----------------------------------------------------

                if len(candidatos) == 1:
                    return candidatos[0]

            return None

        # ============================================================
        # 6. PREPARAR GUARDADO
        # ============================================================

        recetas_nuevas = []
        salidas_nuevas = []

        folios_guardados = []
        medicamentos_no_encontrados = []

        detalles_creados = 0
        salidas_creadas = 0

        # ============================================================
        # 7. PROCESAR CADA FOLIO
        # ============================================================

        for folio, lista_medicamentos in folios_nuevos.items():

            print("\n" + "-" * 60)
            print(f">>> PROCESANDO FOLIO: {folio}")
            print(f">>> MEDICAMENTOS: {len(lista_medicamentos)}")
            print("-" * 60)

            # --------------------------------------------------------
            # DETERMINAR TIPO DE SURTIMIENTO
            # --------------------------------------------------------

            cantidades_surtidas = []

            for med in lista_medicamentos:

                try:
                    surtida = int(med.get("Surtida", 0) or 0)
                except (ValueError, TypeError):
                    surtida = 0

                cantidades_surtidas.append(surtida)

            if not cantidades_surtidas:

                tipo_surtimiento = "No surtida"

            elif all(c == 0 for c in cantidades_surtidas):

                tipo_surtimiento = "No surtida"

            elif all(c > 0 for c in cantidades_surtidas):

                tipo_surtimiento = "Completa"

            else:

                tipo_surtimiento = "Parcial"

            print(f">>> TIPO SURTIMIENTO: {tipo_surtimiento}")

            # ========================================================
            # CREAR RECETA
            #
            # IMPORTANTE:
            # La receta se crea aunque TODOS sus medicamentos tengan
            # Surtida = 0.
            # ========================================================

            nueva_receta = RecetaMedica(

                folio=folio,

                fecha_emision=datetime.utcnow(),

                id_paciente=64,

                id_usuario=(
                    current_user.id_usuario
                    if hasattr(current_user, "id_usuario")
                    else 1
                ),

                id_asignacion=2,

                diagnostico_id=1,

                tipo_surtimiento=tipo_surtimiento,

                nota_id=5
            )

            detalles_folio = 0

            # ========================================================
            # 8. PROCESAR MEDICAMENTOS
            # ========================================================

            for med in lista_medicamentos:

                clave_receta = str(
                    med.get("Clave", "")
                ).strip()

                try:
                    cantidad_surtida = int(
                        med.get("Surtida", 0) or 0
                    )
                except (ValueError, TypeError):
                    cantidad_surtida = 0

                # Nunca aceptar cantidades negativas provenientes
                # del archivo/auditoría.
                if cantidad_surtida < 0:
                    cantidad_surtida = 0

                encontrado = buscar_medicamento(
                    clave_receta
                )

                # ----------------------------------------------------
                # MEDICAMENTO NO ENCONTRADO
                # ----------------------------------------------------

                if encontrado is None:

                    medicamentos_no_encontrados.append({
                        "folio": folio,
                        "clave": clave_receta
                    })

                    print(
                        f"MEDICAMENTO NO ENCONTRADO: "
                        f"FOLIO: {folio} "
                        f"CLAVE: {clave_receta}"
                    )

                    # IMPORTANTE:
                    # NO eliminamos la receta completa.
                    # Continuamos con el siguiente medicamento.
                    continue

                medicamento_db = encontrado["medicamento"]
                inventario = encontrado["inventario"]

                print(
                    f">>> ENCONTRADO: "
                    f"{clave_receta} -> "
                    f"{medicamento_db.clave}"
                )

                # ====================================================
                # 9. CREAR DETALLE
                #
                # SE CREA INCLUSO SI Surtida = 0
                # ====================================================

                detalle = DetalleReceta(

                    id_medicamento=medicamento_db.id_medicamento,

                    cantidad=cantidad_surtida
                )

                nueva_receta.detalle.append(detalle)

                detalles_creados += 1
                detalles_folio += 1

                # ====================================================
                # 10. INVENTARIO
                #
                # SOLO se modifica si realmente se surtió.
                #
                # NUNCA permitimos:
                #
                # existencia = -1
                # existencia = -5
                #
                # El mínimo siempre será 0.
                # ====================================================

                if cantidad_surtida > 0:

                    if inventario is None:

                        # ------------------------------------------------
                        # No existe inventario.
                        #
                        # NO creamos inventario negativo.
                        # La salida se registra como surtida,
                        # pero la existencia local queda en 0.
                        # ------------------------------------------------

                        print(
                            f">>> SIN INVENTARIO: "
                            f"{medicamento_db.clave} "
                            f"NO SE CREA EXISTENCIA NEGATIVA"
                        )

                        lote_val = "SIN LOTE"
                        fecha_venc = None

                    else:

                        existencia_anterior = (
                            inventario.cantidad or 0
                        )

                        existencia_anterior = max(
                            0,
                            existencia_anterior
                        )

                        existencia_nueva = max(
                            0,
                            existencia_anterior -
                            cantidad_surtida
                        )

                        inventario.cantidad = existencia_nueva

                        lote_val = (
                            inventario.lote
                            or "SIN LOTE"
                        )

                        fecha_venc = (
                            inventario.fecha_vencimiento
                        )

                        print(
                            f">>> INVENTARIO: "
                            f"{medicamento_db.clave} "
                            f"{existencia_anterior} -> "
                            f"{existencia_nueva}"
                        )

                    # ====================================================
                    # 11. CREAR SALIDA
                    # ====================================================

                    salida = SalidaFarmacia(

                        id_medicamento=(
                            medicamento_db.id_medicamento
                        ),

                        cantidad=cantidad_surtida,

                        lote=lote_val,

                        fecha_vencimiento=fecha_venc,

                        fecha_salida=datetime.utcnow(),

                        id_usuario=(
                            current_user.id_usuario
                            if hasattr(
                                current_user,
                                "id_usuario"
                            )
                            else 1
                        ),

                        tipo_salida="RECETA",

                        receta=nueva_receta
                    )

                    salidas_nuevas.append(salida)

                    salidas_creadas += 1

            # ========================================================
            # 12. GUARDAR LA RECETA
            #
            # ESTA ES LA CORRECCIÓN IMPORTANTE:
            #
            # Antes probablemente se hacía:
            #
            # if nueva_receta.detalle:
            #
            # y eso hacía que una receta pudiera perderse.
            #
            # Ahora:
            #
            # - Si tiene medicamentos encontrados -> se guarda.
            # - Incluso si todos tienen Surtida = 0.
            #
            # Si NINGÚN medicamento existe en BD, no podemos crear
            # detalles válidos y se informa como problema.
            # ========================================================

            if detalles_folio > 0:

                recetas_nuevas.append(
                    nueva_receta
                )

                folios_guardados.append(
                    folio
                )

                print(
                    f">>> RECETA PREPARADA: "
                    f"{folio} "
                    f"DETALLES: {detalles_folio}"
                )

            else:

                print(
                    f">>> NO SE PUEDE GUARDAR FOLIO {folio}: "
                    f"NINGÚN MEDICAMENTO ENCONTRADO EN BD"
                )

        # ============================================================
        # 13. SI NO HAY RECETAS PARA GUARDAR
        # ============================================================

        if not recetas_nuevas:

            db.session.rollback()

            print("\n" + "=" * 60)
            print(">>> NO HAY RECETAS PARA GUARDAR")
            print("=" * 60)

            return jsonify({

                "status": "warning",

                "guardados": 0,

                "omitidos": len(folios_existentes),

                "folios_omitidos": sorted(
                    folios_existentes
                ),

                "no_encontrados":
                    len(medicamentos_no_encontrados),

                "message":
                    "No se pudo guardar ninguna receta. "
                    "Revisar las claves no encontradas."

            }), 200

        # ============================================================
        # 14. GUARDADO
        # ============================================================

        db.session.add_all(
            recetas_nuevas
        )

        db.session.add_all(
            salidas_nuevas
        )

        db.session.commit()

        # ============================================================
        # 15. VERIFICACIÓN DE EXISTENCIAS NEGATIVAS
        # ============================================================

        inventarios_negativos = (
            db.session.query(InventarioFarmacia)
            .filter(
                InventarioFarmacia.cantidad < 0
            )
            .count()
        )

        if inventarios_negativos > 0:

            print(
                "!!! ADVERTENCIA: "
                f"{inventarios_negativos} inventarios "
                "tienen existencia negativa."
            )

        # ============================================================
        # 16. RESUMEN FINAL
        # ============================================================

        print("\n" + "=" * 70)
        print(">>> GUARDADO COMPLETADO")
        print("=" * 70)

        print(
            f"FOLIOS RECIBIDOS: "
            f"{len(folios_enviados)}"
        )

        print(
            f"FOLIOS YA EXISTENTES: "
            f"{len(folios_existentes)}"
        )

        print(
            f"FOLIOS NUEVOS: "
            f"{len(folios_nuevos)}"
        )

        print(
            f"RECETAS CREADAS: "
            f"{len(folios_guardados)}"
        )

        print(
            f"DETALLES CREADOS: "
            f"{detalles_creados}"
        )

        print(
            f"SALIDAS CREADAS: "
            f"{salidas_creadas}"
        )

        print(
            f"MEDICAMENTOS NO ENCONTRADOS: "
            f"{len(medicamentos_no_encontrados)}"
        )

        print("=" * 70)

        return jsonify({

            "status": "success",

            "guardados":
                len(folios_guardados),

            "folios_guardados":
                folios_guardados,

            "omitidos":
                len(folios_existentes),

            "folios_omitidos":
                sorted(folios_existentes),

            "detalles":
                detalles_creados,

            "salidas":
                salidas_creadas,

            "medicamentos_no_encontrados":
                medicamentos_no_encontrados,

            "message":
                f"Se guardaron "
                f"{len(folios_guardados)} folios."

        }), 200

    # ================================================================
    # ERRORES
    # ================================================================

    except IntegrityError as e:

        db.session.rollback()

        print("\n" + "=" * 70)
        print(">>> ERROR DE INTEGRIDAD")
        print("=" * 70)

        print(str(e.orig))

        return jsonify({

            "status": "error",

            "message":
                "Error de integridad.",

            "detalle":
                str(e.orig)

        }), 500

    except OperationalError as e:

        db.session.rollback()

        print("\n" + "=" * 70)
        print(">>> ERROR OPERACIONAL DE BD")
        print("=" * 70)

        print(str(e))

        return jsonify({

            "status": "error",

            "message":
                "No fue posible conectarse "
                "con la base de datos."

        }), 503

    except Exception as e:

        db.session.rollback()

        print("\n" + "=" * 70)
        print(">>> ERROR GENERAL EN guardar_dia")
        print("=" * 70)

        print(
            f"{type(e).__name__}: {str(e)}"
        )

        return jsonify({

            "status": "error",

            "message":
                str(e)

        }), 500



#______________________________________________________________________________________________________________________________________________
from datetime import datetime

@bp.route("/generador", methods=["GET", "POST"])
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def generador():
    if request.method == "POST":
        file_reporte = request.files.get("archivo_reporte")
        file_catalogo = request.files.get("archivo_catalogo")
        file_entrada = request.files.get("archivo_entrada") 

        if not file_reporte or not file_catalogo:
            return "Error: Faltan archivos base."

        # Obtenemos Año y Mes actual (ej. 2026-04)
        ahora = datetime.now()
        anio_actual = ahora.year
        mes_actual = ahora.month

        # 1. CARGAR DATOS BASE
        df_rep = pd.read_excel(file_reporte)
        df_cat = pd.read_excel(file_catalogo)

        def normalizar(c):
            return str(c).strip().upper().replace("Ó", "O").replace("Í", "I")

        df_rep.columns = [normalizar(c) for c in df_rep.columns]
        df_cat.columns = [normalizar(c) for c in df_cat.columns]

        col_clave = next((c for c in df_cat.columns if 'CLAVE' in c), 'CLAVE')
        col_desc = next((c for c in df_cat.columns if 'DESCRIPCION' in c or 'DESC' in c), None)
        col_existencia = next((c for c in df_cat.columns if 'EXISTENCIA' in c or 'STOCK' in c), None)

        # 2. MAPEAR DESCRIPCIONES Y STOCK INICIAL
        control_stock = {}
        control_descripciones = {}
        for _, row in df_cat.iterrows():
            c = str(row[col_clave]).strip()
            d = str(row[col_desc]).strip() if col_desc else "SIN DESCRIPCIÓN"
            control_descripciones[c] = f"{c} {d}"
            try:
                control_stock[c] = int(float(row[col_existencia])) if col_existencia else 0
            except:
                control_stock[c] = 0

        # 3. PREPARAR ENTRADAS (MATRIZ OC99)
        entradas_por_dia = {}
        if file_entrada:
            df_ent = pd.read_excel(file_entrada)
            df_ent.columns = [str(c).strip() for c in df_ent.columns]
            col_ent_clave = next((c for c in df_ent.columns if 'CLAVE' in c.upper()), 'CLAVE')
            columnas_dias_ent = [c for c in df_ent.columns if c.isdigit()]
            
            for d in columnas_dias_ent:
                entradas_por_dia[d] = {}
                for _, row in df_ent.iterrows():
                    c_ent = str(row[col_ent_clave]).strip()
                    if c_ent in control_stock:
                        try:
                            entradas_por_dia[d][c_ent] = int(float(row[d]))
                        except: continue

        # 4. PROCESO CRONOLÓGICO POR DÍA
        dias_presentes = sorted([str(i) for i in range(1, 32) if str(i) in df_rep.columns], key=int)
        df_rep[col_clave] = df_rep[col_clave].astype(str).str.strip()
        
        json_maestro = []

        for dia in dias_presentes:
            # Fecha dinámica según el mes y año en curso
            fecha_registro = f"{anio_actual}-{mes_actual:02d}-{int(dia):02d}"
            
            # --- A. ENTRADAS DE LA MATRIZ (OC99) ---
            if dia in entradas_por_dia:
                for clv, cant in entradas_por_dia[dia].items():
                    if cant > 0:
                        control_stock[clv] += cant
                        json_maestro.append({
                            "Clave": clv,
                            "Medicamento": control_descripciones.get(clv, clv),
                            "CantidadRecibida": cant,
                            "CantidadEntregada": 0,
                            "Stock": control_stock[clv],
                            "CLUES": "CSIMB005343",
                            "Responsable": "PEDRO JESUS GALINDO ESTRADA",
                            "FechaRegistro": fecha_registro,
                            "Versión": "Versión 5"
                        })

            # --- B. SALIDAS DEL DÍA (REGLA ESPEJO) ---
            for _, row in df_rep.iterrows():
                clave = str(row[col_clave]).strip()
                if clave not in control_stock: continue 
                
                try:
                    entrega_dia = int(float(row[dia]))
                except:
                    entrega_dia = 0
                
                if entrega_dia > 0:
                    stock_antes = control_stock[clave]
                    
                    # Cálculo espejo: solo lo faltante
                    recibida_necesaria = entrega_dia - stock_antes if stock_antes < entrega_dia else 0
                    stock_final = (stock_antes + recibida_necesaria) - entrega_dia
                    
                    json_maestro.append({
                        "Clave": clave,
                        "Medicamento": control_descripciones.get(clave, clave),
                        "CantidadRecibida": recibida_necesaria,
                        "CantidadEntregada": entrega_dia,
                        "Stock": stock_final,
                        "CLUES": "CSIMB005343",
                        "Responsable": "PEDRO JESUS GALINDO ESTRADA",
                        "FechaRegistro": fecha_registro,
                        "Versión": "Versión 5"
                    })
                    control_stock[clave] = stock_final

        json_string = json.dumps(json_maestro, ensure_ascii=False)
        return render_template("resultado_json.html", json_data=json_string)

    return render_template("inicio.html")
