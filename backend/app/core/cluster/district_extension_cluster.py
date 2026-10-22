import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

from app.core.cluster.base_cluster import BaseCluster
from app.utils.distance import haversine


class DistrictExtensionCluster(BaseCluster):
    """
    基于行政区划构建业务片区。
    """

    def __init__(self,
                 data: pd.DataFrame,
                 min_zone_size: int = 20,
                 max_zone_size: int = 40,
                 district_col: str = 'district',
                 lng_col: str = 'longitude',
                 lat_col: str = 'latitude',
                 freq_col: str = 'frequency',
                 load_col: str = 'avg_loads'):
        super().__init__()
        self.data = data
        self.min_zone_size = min_zone_size
        self.max_zone_size = max_zone_size
        self.district_col = district_col
        self.lng_col = lng_col
        self.lat_col = lat_col
        self.freq_col = freq_col
        self.load_col = load_col
        self.cluster_center = None

    def getClusterCenter(self):
        return self.cluster_center

    def fit(self, warehouse_lng=None, warehouse_lat=None):
        df = self.data.copy()
        df['_row_idx'] = range(len(df))

        # Step 1: 按行政区划初始分组
        raw_groups = self._group_by_district(df)

        # Step 2: 大区拆分
        split_groups = {}
        for district, group_df in raw_groups.items():
            if len(group_df) > self.max_zone_size:
                sub_groups = self._split_large_district(district, group_df)
                split_groups.update(sub_groups)
            else:
                split_groups[district] = group_df

        # Step 3: 小区合并
        merged_groups = self._merge_small_districts(split_groups)

        # Step 4: 构建 ZoneInfo 并写回 cluster_id
        cluster_id_series = pd.Series(0, index=df.index)
        
        centers_data = []

        for cluster_id, (zone_id, group_df) in enumerate(merged_groups.items()):
            center_lon = group_df[self.lng_col].mean()
            center_lat = group_df[self.lat_col].mean()

            cluster_id_series.iloc[group_df['_row_idx'].values] = cluster_id
            
            centers_data.append({
                'cluster_id': cluster_id,
                'center_lgt': center_lon,
                'center_lat': center_lat
            })

        df['cluster_id'] = cluster_id_series
        df.drop(columns=['_row_idx'], inplace=True)
        self.data = df
        self.cluster_center = pd.DataFrame(centers_data)
        
        self.data = pd.merge(self.data, self.cluster_center, on='cluster_id', how='left')

        if warehouse_lng is not None and warehouse_lat is not None:
            self.cdist_calc(warehouse_lng, warehouse_lat)
            
        return self

    def _group_by_district(self, df: pd.DataFrame) -> dict[str, pd.DataFrame]:
        """按行政区划分组"""
        groups = {}
        for district, group in df.groupby(self.district_col):
            groups[str(district)] = group
        return groups

    def _split_large_district(self, district: str, group_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
        """将大区按地理位置拆分为多个子片区"""
        n_sub = int(np.ceil(len(group_df) / self.max_zone_size))
        coords = group_df[[self.lng_col, self.lat_col]].values

        kmeans = KMeans(n_clusters=n_sub, n_init=10, random_state=42)
        labels = kmeans.fit_predict(coords)

        sub_groups = {}
        for i in range(n_sub):
            mask = labels == i
            sub_id = f"{district}__{i}"
            sub_groups[sub_id] = group_df[mask]
        return sub_groups

    def _merge_small_districts(self, groups: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        """将过小的片区合并到地理上最近的片区"""
        centers = {}
        for gid, gdf in groups.items():
            centers[gid] = (gdf[self.lng_col].mean(), gdf[self.lat_col].mean())

        normal_ids = [gid for gid, gdf in groups.items() if len(gdf) >= self.min_zone_size]
        small_ids = [gid for gid, gdf in groups.items() if len(gdf) < self.min_zone_size]

        if not small_ids:
            return groups

        if not normal_ids:
            largest = max(small_ids, key=lambda gid: len(groups[gid]))
            normal_ids.append(largest)
            small_ids.remove(largest)

        small_ids.sort(key=lambda gid: len(groups[gid]))

        merged_small: dict[str, pd.DataFrame] = {}
        remaining_small = list(small_ids)

        while remaining_small:
            current_id = remaining_small.pop(0)
            current_df = groups[current_id] if current_id in groups else merged_small.pop(current_id)
            current_center = (current_df[self.lng_col].mean(), current_df[self.lat_col].mean())

            merged = False
            for other_id in list(remaining_small):
                other_df = groups[other_id] if other_id in groups else merged_small.get(other_id)
                if other_df is None:
                    continue
                combined_size = len(current_df) + len(other_df)
                if combined_size <= self.max_zone_size:
                    other_center = (other_df[self.lng_col].mean(), other_df[self.lat_col].mean())
                    dist = haversine(current_center[0], current_center[1],
                                    other_center[0], other_center[1])
                    if dist <= 50:
                        new_id = f"{current_id}+{other_id}"
                        new_df = pd.concat([current_df, other_df], ignore_index=False)
                        remaining_small.remove(other_id)
                        if other_id in merged_small:
                            del merged_small[other_id]

                        if len(new_df) >= self.min_zone_size:
                            normal_ids.append(new_id)
                            groups[new_id] = new_df
                        else:
                            merged_small[new_id] = new_df
                            remaining_small.append(new_id)
                        merged = True
                        break

            if not merged:
                min_dist = float('inf')
                best_target = None
                for nid in normal_ids:
                    ndf = groups.get(nid, merged_small.get(nid))
                    if ndf is None:
                        continue
                    n_center = (ndf[self.lng_col].mean(), ndf[self.lat_col].mean())
                    d = haversine(current_center[0], current_center[1],
                                  n_center[0], n_center[1])
                    if d < min_dist:
                        min_dist = d
                        best_target = nid

                if best_target is not None:
                    target_df = groups[best_target]
                    new_df = pd.concat([target_df, current_df], ignore_index=False)
                    new_id = f"{best_target}+{current_id}"
                    groups[new_id] = new_df
                    normal_ids.remove(best_target)
                    normal_ids.append(new_id)
                    if best_target in groups:
                        del groups[best_target]
                else:
                    merged_small[current_id] = current_df

        result = {}
        for nid in normal_ids:
            result[nid] = groups[nid]
        for sid, sdf in merged_small.items():
            result[sid] = sdf

        return result
