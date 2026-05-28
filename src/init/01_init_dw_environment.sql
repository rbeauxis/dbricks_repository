-- Databricks notebook source
-- ==============================================================================
-- Script de Inicialización del Entorno (Data Warehouse / Medallion Architecture)
-- ==============================================================================
-- Este script prepara los esquemas (bases de datos) para las capas gestionadas 
-- del Data Warehouse. 
-- Nota: La zona de "Landing" es externa al catálogo (Workspace/Cloud Storage) 
-- por lo que no se define aquí mediante DDL.

-- 1. SELECCIONAR EL CATÁLOGO
USE CATALOG main;

-- 2. CREACIÓN DE LAS CAPAS DEL DATA WAREHOUSE (MANAGED SCHEMAS)

-- A) Capa RAW (Bronze)
-- Primera capa del Data Warehouse, donde se guardarán las Managed Tables crudas.
CREATE SCHEMA IF NOT EXISTS main.dw_raw
COMMENT 'Capa RAW / Bronze. Datos sin transformar ingestados desde Landing.';

-- B) Capa CURATED (Silver)
-- Capa de datos limpios, estandarizados y unidos.
CREATE SCHEMA IF NOT EXISTS main.dw_curated
COMMENT 'Capa CURATED / Silver. Datos limpios, filtrados y estandarizados.';

-- C) Capa CONSUMPTION (Gold)
-- Capa de modelos dimensionales y agregaciones listas para BI.
CREATE SCHEMA IF NOT EXISTS main.dw_consumption
COMMENT 'Capa CONSUMPTION / Gold. Modelos dimensionales (Estrella) para consumo final.';

-- 3. VALIDACIÓN
-- Listamos los esquemas para confirmar
SHOW SCHEMAS IN main;
