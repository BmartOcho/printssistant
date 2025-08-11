from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
import joblib

"""
Input CSV schema (header row required):
job_number,title,width_in,height_in,pages,label
J123456,"Tri-Fold Brochure",11,8.5,2,trifold
J234567,"Business Card",3.5,2,1,business_card
...
"""

def build_pipeline():
    text = TfidfVectorizer(ngram_range=(1,2), min_df=1, max_features=20000)
    numeric_cols = ["width_in","height_in","pages","long_edge","short_edge","aspect"]
    pre = ColumnTransformer(
        transformers=[
            ("text", text, "title"),
            ("num", Pipeline([("scaler", StandardScaler(with_mean=False))]), numeric_cols),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )
    clf = LogisticRegression(max_iter=2000, n_jobs=None)
    pipe = Pipeline([("pre", pre), ("clf", clf)])
    return pipe

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="training data CSV")
    ap.add_argument("out", help="output model path, e.g., models/product_type.joblib")
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    # derive features
    df["long_edge"] = df[["width_in","height_in"]].max(axis=1)
    df["short_edge"] = df[["width_in","height_in"]].min(axis=1)
    df["aspect"] = (df["long_edge"] / df["short_edge"].replace(0, 1)).round(4)

    X = df[["title","width_in","height_in","pages","long_edge","short_edge","aspect"]]
    y = df["label"].astype(str)

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    pipe = build_pipeline()
    pipe.fit(Xtr, ytr)

    yhat = pipe.predict(Xte)
    print(classification_report(yte, yhat))

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, outp)
    print(f"Saved model → {outp}")

if __name__ == "__main__":
    main()
