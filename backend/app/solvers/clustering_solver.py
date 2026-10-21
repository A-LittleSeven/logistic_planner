import pandas as pd

from app.utils.distance import DistanceProvider, haversine
from app.core import clustering_registry
from app.models.dto.ClusteringDTO import ClusteringSolveRequest


def solve_clustering(req: ClusteringSolveRequest, provider: DistanceProvider) -> dict:
    if not req.points:
        raise ValueError("至少需要 1 个门店点")

    # Build DataFrame from input points, preserving all extra attributes
    data_list = []
    for p in req.points:
        d = p.model_dump()
        if p.model_extra:
            d.update(p.model_extra)
        data_list.append(d)

    df = pd.DataFrame(data_list)
    df["_orig_idx"] = range(len(df))

    # Drop pre-existing center or distance columns to avoid suffix collisions on merges
    cols_to_drop = ["center_lgt", "center_lat", "center_lng", "c_dist", "s_dist", "dist", "store_dist", "cluster_id"]
    for col in cols_to_drop:
        if col in df.columns:
            df.drop(columns=[col], inplace=True)

    # Sanitize attributes to avoid key errors in the algorithms
    if "frequency" not in df.columns:
        df["frequency"] = 1
    else:
        df["frequency"] = df["frequency"].fillna(1).astype(int)

    if "avg_loads" not in df.columns:
        df["avg_loads"] = 1.0
    else:
        df["avg_loads"] = df["avg_loads"].fillna(1.0).astype(float)

    if "district" not in df.columns:
        df["district"] = "未知区划"
    else:
        df["district"] = df["district"].fillna("").astype(str).str.strip()
        # Fallback: if district is empty, attempt to infer from address or name
        for idx, row in df.iterrows():
            if not row["district"] or row["district"] in ["", "nan", "None", "null"]:
                addr = str(row.get("address", "") or "")
                name = str(row.get("name", "") or "")
                extracted = ""
                for target_d in ["青秀区", "兴宁区", "江南区", "西乡塘区", "良庆区", "邕宁区", "武鸣区", "横州市", "宾阳县", "上林县", "马山县", "隆安县"]:
                    if target_d in addr or target_d in name or target_d.replace("区", "") in addr:
                        extracted = target_d
                        break
                df.at[idx, "district"] = extracted if extracted else "未知区划"

    # Use the depot coordinates supplied in request or fallback to center of points
    depot_lng = req.depot_lng
    depot_lat = req.depot_lat

    # Choose algorithm
    alg = req.algorithm
    if alg == "kmeans":
        from app.core import getClusterByConstrainedKmeans
        n_clusters = req.k
        if n_clusters > len(df):
            n_clusters = len(df)
        clusterer = getClusterByConstrainedKmeans(df, n_clusters=n_clusters, lng_col="lng", lat_col="lat", freq_col="frequency")
    elif alg == "district":
        from app.core import ClusterByDistinct
        clusterer = ClusterByDistinct(df, distinct_col="district", lng_col="lng", lat_col="lat")
    elif alg == "district_extension":
        from app.core import ClusterByDistrictExtension
        min_size = req.options.get("min_zone_size", 20)
        max_size = req.options.get("max_zone_size", 40)
        clusterer = ClusterByDistrictExtension(
            df,
            min_zone_size=int(min_size),
            max_zone_size=int(max_size),
            district_col="district",
            lng_col="lng",
            lat_col="lat",
            freq_col="frequency",
            load_col="avg_loads"
        )
    else:
        raise ValueError(f"未知算法: {alg}")

    # Solve using warehouse/depot location
    clusterer.fit(depot_lng, depot_lat)

    res_df = clusterer.data
    
    # Restore the original row order to match the input points
    res_df = res_df.sort_values("_orig_idx").reset_index(drop=True)

    assignments = res_df["cluster_id"].astype(int).tolist()
    unique_clusters = sorted(res_df["cluster_id"].unique())
    k_actual = len(unique_clusters)

    clusters = []
    for cid in unique_clusters:
        cluster_df = res_df[res_df["cluster_id"] == cid]
        # Get center coordinates
        center_lng = float(cluster_df["center_lgt"].iloc[0])
        center_lat = float(cluster_df["center_lat"].iloc[0])
        
        # Calculate cluster distance to warehouse (cdist_warehouse)
        cdist_wh = haversine(center_lng, center_lat, depot_lng, depot_lat)
        
        # Indices of points belonging to this cluster in the original array
        idxs = cluster_df["_orig_idx"].tolist()

        clusters.append({
            "cluster_id": int(cid),
            "center": {
                "lng": center_lng,
                "lat": center_lat
            },
            "size": len(idxs),
            "point_indices": idxs,
            "cdist_warehouse": float(cdist_wh)
        })

    # Return point list enriched with sdist_warehouse and cdist_warehouse
    enriched_points = []
    for idx, row in res_df.iterrows():
        p_lng = float(row["lng"])
        p_lat = float(row["lat"])
        cid = int(row["cluster_id"])
        
        # Find matching cluster center
        matching_c = next(c for c in clusters if c["cluster_id"] == cid)
        c_lng = matching_c["center"]["lng"]
        c_lat = matching_c["center"]["lat"]
        
        # Calculate distances
        sdist_wh = haversine(p_lng, p_lat, depot_lng, depot_lat)
        cdist_wh = haversine(c_lng, c_lat, depot_lng, depot_lat)
        
        point_dict = req.points[idx].model_dump()
        point_dict.update({
            "sdist_warehouse": float(sdist_wh),
            "cdist_warehouse": float(cdist_wh),
            "cluster_id": cid
        })
        enriched_points.append(point_dict)

    return {
        "algorithm": alg,
        "k": k_actual,
        "clusters": clusters,
        "assignments": assignments,
        "points": enriched_points
    }


# Register all three algorithms
clustering_registry.register("kmeans", solve_clustering)
clustering_registry.register("district", solve_clustering)
clustering_registry.register("district_extension", solve_clustering)
