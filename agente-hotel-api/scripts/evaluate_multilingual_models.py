#!/usr/bin/env python3
"""
evaluate_multilingual_models.py
Script para evaluar el rendimiento de modelos NLP multilingües
Fase E.5 - Mejora del Motor NLP
"""

import os
import sys
import argparse
import json
import yaml
import subprocess
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from datetime import datetime

# Configuración de colores para mensajes
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
BLUE = '\033[0;34m'
MAGENTA = '\033[0;35m'
CYAN = '\033[0;36m'
NC = '\033[0m'  # No Color

def print_color(color, message):
    """Imprimir mensaje con color"""
    print(f"{color}{message}{NC}")

def run_command(command, cwd=None):
    """Ejecutar un comando y devolver el resultado"""
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            shell=True
        )
        if result.returncode != 0:
            print_color(RED, f"Error al ejecutar comando: {command}")
            print_color(RED, f"Error: {result.stderr}")
            return None
        return result.stdout
    except Exception as e:
        print_color(RED, f"Excepción al ejecutar comando {command}: {e}")
        return None

def load_yaml_file(file_path):
    """Cargar archivo YAML"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except Exception as e:
        print_color(RED, f"Error al cargar {file_path}: {e}")
        return None

def load_json_file(file_path):
    """Cargar archivo JSON"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        print_color(RED, f"Error al cargar {file_path}: {e}")
        return None

def save_json_file(data, file_path):
    """Guardar archivo JSON"""
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2)
        return True
    except Exception as e:
        print_color(RED, f"Error al guardar {file_path}: {e}")
        return False

def create_test_splits(nlu_files, output_dir, test_ratio=0.2):
    """
    Crear divisiones de entrenamiento/prueba para cada idioma
    
    Args:
        nlu_files: Lista de archivos NLU por idioma
        output_dir: Directorio de salida
        test_ratio: Proporción de ejemplos para prueba
    
    Returns:
        Diccionario con rutas a los archivos divididos
    """
    import random
    
    output_files = {}
    
    for nlu_file in nlu_files:
        data = load_yaml_file(nlu_file)
        if not data or 'nlu' not in data:
            continue
            
        # Determinar el idioma del archivo
        lang = "unknown"
        if '_en' in nlu_file:
            lang = "en"
        elif '_pt' in nlu_file:
            lang = "pt"
        else:
            lang = "es"  # Valor predeterminado para español
            
        # Crear directorios si no existen
        train_dir = os.path.join(output_dir, 'train')
        test_dir = os.path.join(output_dir, 'test')
        os.makedirs(train_dir, exist_ok=True)
        os.makedirs(test_dir, exist_ok=True)
        
        # Crear estructuras para train y test
        train_data = {"version": "3.1", "nlu": []}
        test_data = {"version": "3.1", "nlu": []}
        
        for intent_entry in data['nlu']:
            if 'intent' not in intent_entry or 'examples' not in intent_entry:
                continue
                
            intent_name = intent_entry['intent']
            examples = intent_entry['examples'].strip().split('\n')
            examples = [line.strip() for line in examples if line.strip()]
            
            # Mezclar ejemplos
            random.shuffle(examples)
            
            # Dividir en train y test
            split_idx = max(1, int(len(examples) * (1 - test_ratio)))
            train_examples = examples[:split_idx]
            test_examples = examples[split_idx:]
            
            # Agregar a los conjuntos correspondientes
            train_data['nlu'].append({
                'intent': intent_name,
                'examples': '\n'.join(train_examples)
            })
            
            if test_examples:  # Solo agregar si hay ejemplos de prueba
                test_data['nlu'].append({
                    'intent': intent_name,
                    'examples': '\n'.join(test_examples)
                })
        
        # Guardar archivos
        train_file = os.path.join(train_dir, f"train_{lang}.yml")
        test_file = os.path.join(test_dir, f"test_{lang}.yml")
        
        with open(train_file, 'w', encoding='utf-8') as f:
            yaml.dump(train_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
        with open(test_file, 'w', encoding='utf-8') as f:
            yaml.dump(test_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
            
        output_files[lang] = {
            'train': train_file,
            'test': test_file
        }
        
        print_color(GREEN, f"Creados archivos de train/test para {lang}")
        print(f"  - Train: {train_file} ({len(train_examples)} ejemplos)")
        print(f"  - Test: {test_file} ({len(test_examples)} ejemplos)")
    
    return output_files

def train_models(base_dir, splits, langs, config_file):
    """
    Entrenar modelos para cada idioma y un modelo multilingüe
    
    Args:
        base_dir: Directorio base
        splits: Divisiones de train/test por idioma
        langs: Lista de idiomas
        config_file: Archivo de configuración
    
    Returns:
        Diccionario con rutas a los modelos entrenados
    """
    models = {}
    models_dir = os.path.join(base_dir, 'models')
    os.makedirs(models_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Entrenar modelo multilingüe primero
    print_color(BLUE, "Entrenando modelo multilingüe...")
    
    # Preparar archivos de entrenamiento multilingüe
    train_files = [splits[lang]['train'] for lang in langs]
    train_files_arg = " ".join(train_files)
    
    model_name = f"multilingual_{timestamp}.tar.gz"
    model_path = os.path.join(models_dir, model_name)
    
    # Ejecutar entrenamiento multilingüe
    train_cmd = f"rasa train nlu --config {config_file} --nlu {train_files_arg} --out {models_dir} --fixed-model-name {model_name}"
    run_command(train_cmd)
    
    models['multilingual'] = model_path
    
    # Entrenar modelos por idioma
    for lang in langs:
        print_color(BLUE, f"Entrenando modelo para {lang}...")
        lang_model_name = f"{lang}_{timestamp}.tar.gz"
        lang_model_path = os.path.join(models_dir, lang_model_name)
        
        train_cmd = f"rasa train nlu --config {config_file} --nlu {splits[lang]['train']} --out {models_dir} --fixed-model-name {lang_model_name}"
        run_command(train_cmd)
        
        models[lang] = lang_model_path
    
    return models

def evaluate_models(models, splits, langs, output_dir):
    """
    Evaluar modelos entrenados con datos de prueba
    
    Args:
        models: Diccionario con rutas a modelos
        splits: Divisiones de train/test por idioma
        langs: Lista de idiomas
        output_dir: Directorio para resultados
    
    Returns:
        Resultados de evaluación
    """
    results = {}
    eval_dir = os.path.join(output_dir, 'evaluation')
    os.makedirs(eval_dir, exist_ok=True)
    
    # Evaluar modelo multilingüe en cada idioma
    if 'multilingual' in models:
        results['multilingual'] = {}
        
        for lang in langs:
            print_color(BLUE, f"Evaluando modelo multilingüe en {lang}...")
            lang_eval_dir = os.path.join(eval_dir, f"multilingual_{lang}")
            os.makedirs(lang_eval_dir, exist_ok=True)
            
            # Ejecutar evaluación
            eval_cmd = f"rasa test nlu --model {models['multilingual']} --nlu {splits[lang]['test']} --out {lang_eval_dir}"
            run_command(eval_cmd)
            
            # Cargar resultados
            intent_report_path = os.path.join(lang_eval_dir, 'intent_report.json')
            if os.path.exists(intent_report_path):
                intent_report = load_json_file(intent_report_path)
                results['multilingual'][lang] = {
                    'intent_report': intent_report,
                    'accuracy': intent_report.get('accuracy', 0),
                    'weighted_avg': intent_report.get('weighted avg', {})
                }
    
    # Evaluar modelos específicos de idioma
    for lang in langs:
        if lang in models:
            print_color(BLUE, f"Evaluando modelo específico de {lang}...")
            lang_eval_dir = os.path.join(eval_dir, f"{lang}_specific")
            os.makedirs(lang_eval_dir, exist_ok=True)
            
            # Ejecutar evaluación
            eval_cmd = f"rasa test nlu --model {models[lang]} --nlu {splits[lang]['test']} --out {lang_eval_dir}"
            run_command(eval_cmd)
            
            # Cargar resultados
            intent_report_path = os.path.join(lang_eval_dir, 'intent_report.json')
            if os.path.exists(intent_report_path):
                intent_report = load_json_file(intent_report_path)
                
                if lang not in results:
                    results[lang] = {}
                    
                results[lang]['specific'] = {
                    'intent_report': intent_report,
                    'accuracy': intent_report.get('accuracy', 0),
                    'weighted_avg': intent_report.get('weighted avg', {})
                }
    
    return results

def generate_comparison_report(results, output_dir):
    """
    Generar informe de comparación entre modelos
    
    Args:
        results: Resultados de evaluación
        output_dir: Directorio para informe
    """
    summary = {
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'models_compared': list(results.keys()),
        'metrics': {},
        'language_performance': {},
        'conclusion': ""
    }
    
    # Extraer métricas relevantes
    metrics_table = []
    
    # Modelo multilingüe
    if 'multilingual' in results:
        for lang, lang_result in results['multilingual'].items():
            w_avg = lang_result.get('weighted_avg', {})
            metrics_table.append({
                'model': 'multilingual',
                'language': lang,
                'accuracy': lang_result.get('accuracy', 0),
                'f1': w_avg.get('f1-score', 0),
                'precision': w_avg.get('precision', 0),
                'recall': w_avg.get('recall', 0)
            })
    
    # Modelos específicos
    for lang in results:
        if lang != 'multilingual' and 'specific' in results[lang]:
            specific = results[lang]['specific']
            w_avg = specific.get('weighted_avg', {})
            metrics_table.append({
                'model': f'{lang} specific',
                'language': lang,
                'accuracy': specific.get('accuracy', 0),
                'f1': w_avg.get('f1-score', 0),
                'precision': w_avg.get('precision', 0),
                'recall': w_avg.get('recall', 0)
            })
    
    # Convertir a DataFrame para facilitar el análisis
    df = pd.DataFrame(metrics_table)
    summary['metrics'] = df.to_dict(orient='records')
    
    # Comparación por idioma
    languages = df['language'].unique()
    for lang in languages:
        lang_df = df[df['language'] == lang]
        
        if len(lang_df) > 1:  # Si tenemos múltiples modelos para comparar
            multi_row = lang_df[lang_df['model'] == 'multilingual']
            specific_row = lang_df[lang_df['model'] == f'{lang} specific']
            
            if not multi_row.empty and not specific_row.empty:
                multi_f1 = multi_row.iloc[0]['f1']
                specific_f1 = specific_row.iloc[0]['f1']
                diff_percentage = ((multi_f1 - specific_f1) / specific_f1) * 100
                
                winner = "multilingual" if multi_f1 > specific_f1 else f"{lang} specific"
                
                summary['language_performance'][lang] = {
                    'multilingual_f1': multi_f1,
                    'specific_f1': specific_f1,
                    'difference_percentage': diff_percentage,
                    'winner': winner
                }
    
    # Conclusiones generales
    if df['model'].str.contains('multilingual').any():
        avg_multi = df[df['model'] == 'multilingual']['f1'].mean()
        avg_specific = df[~df['model'].str.contains('multilingual')]['f1'].mean()
        
        if avg_multi > avg_specific:
            summary['conclusion'] = f"El modelo multilingüe supera a los modelos específicos en un promedio de {((avg_multi - avg_specific) / avg_specific) * 100:.2f}% en F1-score."
        else:
            summary['conclusion'] = f"Los modelos específicos de idioma superan al modelo multilingüe en un promedio de {((avg_specific - avg_multi) / avg_multi) * 100:.2f}% en F1-score."
    
    # Visualizar resultados
    plt.figure(figsize=(12, 8))
    
    # Gráfico de barras agrupadas para F1-score
    languages = df['language'].unique()
    x = np.arange(len(languages))
    width = 0.35
    
    multi_f1 = []
    specific_f1 = []
    
    for lang in languages:
        lang_df = df[df['language'] == lang]
        
        multi_row = lang_df[lang_df['model'] == 'multilingual']
        if not multi_row.empty:
            multi_f1.append(multi_row.iloc[0]['f1'])
        else:
            multi_f1.append(0)
            
        specific_row = lang_df[lang_df['model'] == f'{lang} specific']
        if not specific_row.empty:
            specific_f1.append(specific_row.iloc[0]['f1'])
        else:
            specific_f1.append(0)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    rects1 = ax.bar(x - width/2, multi_f1, width, label='Multilingüe')
    rects2 = ax.bar(x + width/2, specific_f1, width, label='Específico')
    
    ax.set_title('Comparación de F1-Score por Idioma y Tipo de Modelo')
    ax.set_xlabel('Idioma')
    ax.set_ylabel('F1-Score')
    ax.set_xticks(x)
    ax.set_xticklabels(languages)
    ax.legend()
    
    # Añadir etiquetas
    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height:.2f}',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom')
    
    autolabel(rects1)
    autolabel(rects2)
    
    plt.tight_layout()
    
    # Guardar gráfico
    plot_path = os.path.join(output_dir, 'model_comparison.png')
    plt.savefig(plot_path)
    
    # Guardar informe JSON
    report_path = os.path.join(output_dir, 'comparison_report.json')
    save_json_file(summary, report_path)
    
    print_color(GREEN, f"Informe de comparación generado: {report_path}")
    print_color(GREEN, f"Gráfico guardado: {plot_path}")
    
    return summary

def main():
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description="Evaluación de modelos NLP multilingües")
    parser.add_argument('--rasa-dir', type=str, default='../rasa_nlu',
                        help='Directorio base de Rasa NLU con datos existentes')
    parser.add_argument('--output-dir', type=str, default='../evaluation',
                        help='Directorio donde se guardarán los resultados de evaluación')
    parser.add_argument('--test-ratio', type=float, default=0.2,
                        help='Proporción de datos a usar para pruebas (0.0-1.0)')
    args = parser.parse_args()
    
    # Determinar rutas absolutas
    script_dir = os.path.dirname(os.path.realpath(__file__))
    rasa_dir = os.path.abspath(os.path.join(script_dir, args.rasa_dir))
    output_dir = os.path.abspath(os.path.join(script_dir, args.output_dir))
    
    # Encabezado
    print_color(GREEN, "==================================================")
    print_color(GREEN, "   Evaluación de Modelos NLP Multilingües - Fase E.5")
    print_color(GREEN, "==================================================")
    print(f"Directorio de datos Rasa: {rasa_dir}")
    print(f"Directorio de salida: {output_dir}")
    print(f"Proporción de prueba: {args.test_ratio}")
    print()
    
    # Verificar que el directorio rasa_dir exista
    if not os.path.isdir(rasa_dir):
        print_color(RED, f"Error: El directorio Rasa NLU no existe: {rasa_dir}")
        sys.exit(1)
        
    # Crear directorio de salida
    os.makedirs(output_dir, exist_ok=True)
    
    # Idiomas soportados
    langs = ['es', 'en', 'pt']
    
    # Verificar archivos NLU
    nlu_files = [
        os.path.join(rasa_dir, 'data', 'nlu.yml'),      # Español (predeterminado)
        os.path.join(rasa_dir, 'data', 'nlu_en.yml'),   # Inglés
        os.path.join(rasa_dir, 'data', 'nlu_pt.yml')    # Portugués
    ]
    
    for file_path in nlu_files:
        if not os.path.isfile(file_path):
            print_color(YELLOW, f"Advertencia: Archivo no encontrado: {file_path}")
    
    # Archivo de configuración
    config_file = os.path.join(rasa_dir, 'config_enhanced.yml')
    if not os.path.isfile(config_file):
        print_color(RED, f"Error: Archivo de configuración no encontrado: {config_file}")
        sys.exit(1)
    
    # Crear divisiones de train/test
    print_color(YELLOW, "Creando divisiones de train/test...")
    splits = create_test_splits(nlu_files, output_dir, args.test_ratio)
    
    # Entrenar modelos
    print_color(YELLOW, "Entrenando modelos...")
    models = train_models(output_dir, splits, langs, config_file)
    
    # Evaluar modelos
    print_color(YELLOW, "Evaluando modelos...")
    results = evaluate_models(models, splits, langs, output_dir)
    
    # Generar informe comparativo
    print_color(YELLOW, "Generando informe comparativo...")
    summary = generate_comparison_report(results, output_dir)
    
    # Conclusión
    print()
    print_color(GREEN, "==================================================")
    print_color(GREEN, "   Evaluación completada")
    print_color(GREEN, "==================================================")
    print_color(CYAN, "Conclusión:")
    print(summary['conclusion'])
    print()
    print(f"Resultados detallados en: {output_dir}")
    
if __name__ == "__main__":
    main()