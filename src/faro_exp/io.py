import hashlib
import json
import os
import tempfile
from pathlib import Path

import jsonschema
import numpy as np
import pandas as pd

FILES = {
    "eligible": "eligible_accounts.parquet",
    "assignment": "assignments.parquet",
    "recorded": "recorded_assignments.parquet",
    "outcome": "outcomes.parquet",
    "event": "delivery_events.jsonl",
}


def encoded(value):
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
            indent=2,
            default=lambda x: x.item() if isinstance(x, np.generic) else str(x),
        ).encode()
        + b"\n"
    )


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        tmp.write(encoded(value))
    os.replace(tmp.name, path)


def read(path):
    return json.loads(Path(path).read_bytes())


def protocol():
    path = Path("experiment_protocols/v1.json")
    obj = read(path)
    if sha(encoded(obj)) != read("contracts.lock.json")["protocol"]:
        raise ValueError("Protocolo v1 alterado")
    return obj


def schema(name):
    path = Path("contracts/v1") / f"{name}.json"
    if file_hash(path) != read("contracts.lock.json")["files"][path.name]:
        raise ValueError("Contrato alterado")
    return read(path)


def validate_document(name, obj):
    jsonschema.validate(
        obj, schema(name), format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER
    )


def frame_contract(name, frame, experiment):
    spec = schema("assignment" if name == "recorded" else name)["properties"]
    if set(frame) != set(spec) or len(frame.columns) != len(spec):
        raise ValueError(f"Columnas incompatibles en {name}")
    frame = frame[list(spec)].copy()
    for col, rules in spec.items():
        values = frame[col]
        if values.isna().any():
            raise ValueError(f"Campo ausente en {name}.{col}")
        if rules.get("format") == "date-time":
            if not isinstance(values.dtype, pd.DatetimeTZDtype):
                if not values.map(lambda v: isinstance(v, str) and v.endswith("Z")).all():
                    raise ValueError(f"Se requiere UTC explícito en {col}")
            frame[col] = pd.to_datetime(values, utc=True, format="ISO8601")
        elif rules["type"] == "integer":
            if (
                not pd.api.types.is_integer_dtype(values)
                or (values < rules.get("minimum", 0)).any()
            ):
                raise ValueError(f"Entero fuera de dominio en {col}")
        elif rules["type"] == "number":
            if not pd.api.types.is_numeric_dtype(values) or not np.isfinite(values).all():
                raise ValueError(f"Número inválido en {col}")
        elif rules["type"] == "boolean":
            if not pd.api.types.is_bool_dtype(values):
                raise ValueError(f"Booleano inválido en {col}")
        elif not values.map(lambda v: isinstance(v, str) and 0 < len(v) <= 120).all():
            raise ValueError(f"Texto inválido en {col}")
        if "enum" in rules and not values.isin(rules["enum"]).all():
            raise ValueError(f"Categoría incompatible en {col}")
    if not frame.experiment_id.eq(experiment).all():
        raise ValueError("Datos de otro experimento")
    return frame


def write_frame(path, frame):
    if path.suffix == ".parquet":
        frame.to_parquet(path, index=False, compression="zstd")
    else:
        path.write_bytes(
            frame.to_json(orient="records", lines=True, date_format="iso", date_unit="s").encode()
        )


def load_bundle(path, kinds):
    path = Path(path)
    manifest = read(path / "manifest.json")
    if set(manifest["files"]) != {FILES[k] for k in kinds} or manifest["protocol_sha256"] != sha(
        encoded(protocol())
    ):
        raise ValueError("Manifiesto o versión de protocolo incompatible")
    frames = {}
    for k in kinds:
        f = path / FILES[k]
        if file_hash(f) != manifest["files"][f.name]:
            raise ValueError(f"Huella incompatible: {f.name}")
        if f.suffix == ".parquet":
            data = pd.read_parquet(f)
        else:
            data = pd.read_json(f, lines=True, convert_dates=False)
        frames[k] = frame_contract(k, data, manifest["experiment_id"])
    return manifest, frames


def bundle(folder, meta, frames):
    folder = Path(folder)
    folder.parent.mkdir(parents=True, exist_ok=True)
    # Prepare all files privately. An interrupted producer leaves no published manifest.
    with tempfile.TemporaryDirectory(dir=folder.parent) as stage:
        tmp = Path(stage)
        for k, frame in frames.items():
            write_frame(tmp / FILES[k], frame)
        manifest = {
            **meta,
            "protocol_sha256": sha(encoded(protocol())),
            "files": {FILES[k]: file_hash(tmp / FILES[k]) for k in frames},
        }
        save(tmp / "manifest.json", manifest)
        if folder.exists():
            old, _ = load_bundle(folder, list(frames))
            if old != manifest:
                raise ValueError("La carpeta pertenece a otra versión de datos")
        else:
            # Rename a child to leave TemporaryDirectory ownership independent.
            publish = tmp / "publish"
            publish.mkdir()
            for f in list(tmp.iterdir()):
                if f != publish:
                    f.rename(publish / f.name)
            publish.rename(folder)
    return manifest


def clock(value):
    result = pd.Timestamp(value)
    if result.tz is None:
        raise ValueError("El corte requiere zona horaria explícita")
    return result.tz_convert("UTC")


def log(stage, **fields):
    print(json.dumps({"stage": stage, **fields}, ensure_ascii=False, default=str), flush=True)
