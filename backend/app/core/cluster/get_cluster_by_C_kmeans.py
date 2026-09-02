import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from sklearn.cluster import KMeans

from app.core.cluster.baseCluster import BaseCluster


class getClusterByConstrainedKmeans(BaseCluster):
    def __init__(self, data: pd.DataFrame,
                 n_clusters,
                 lng_col='longitude',
                 lat_col='latitude',
                 freq_col='frequency',
                 max_iter=300,
                 tol=1e-4):
        super().__init__()
        self.data = data
        self.n_clusters = n_clusters
        self.lng_col = lng_col
        self.lat_col = lat_col
        self.freq_col = freq_col
        self.max_iter = max_iter
        self.tol = tol
        self.cluster_center = None
        self.delivery_freq = None

    def _get_min_cluster_size(self, cluster_delivery_freq):
        """根据配送频率确定最小聚类规模"""
        if len(cluster_delivery_freq) > 0:
            max_freq = np.max(cluster_delivery_freq)
            min_size = max_freq * 13
        else:
            min_size = 13
        return min_size

    def _init_centers(self, X):
        """改进的初始化：考虑空间分布和约束"""
        kmeans = KMeans(n_clusters=self.n_clusters, n_init=10, random_state=42)
        kmeans.fit(X)
        centers = kmeans.cluster_centers_
        return centers

    def getClusterCenter(self):
        """返回聚类中心 DataFrame，包含 center_lgt、center_lat、cluster_id"""
        df_center = pd.DataFrame(self.cluster_centers_, columns=["center_lgt", "center_lat"])
        df_center["cluster_id"] = range(len(df_center))
        return df_center

    def _assign_with_strong_constraints(self, X, centers, delivery_freq):
        """带强约束的分配步骤"""
        n_samples = X.shape[0]
        distances = cdist(X, centers, metric='euclidean')
        labels = np.argmin(distances, axis=1)
        labels = self._enforce_strong_constraints(X, labels, delivery_freq, distances)
        return labels

    def _enforce_strong_constraints(self, X, labels, delivery_freq, distances):
        """强制执行强约束的算法"""
        max_iterations = 1000

        for iteration in range(max_iterations):
            violations = self._check_all_violations(labels, delivery_freq)
            if not violations:
                break

            under_violations = [v for v in violations if v[2] == 'under']
            for cluster_id, violation_amount, _ in under_violations:
                self._add_points_to_cluster_strong(X, labels, cluster_id, violation_amount, distances, delivery_freq)

            violations = self._check_all_violations(labels, delivery_freq)
            if not violations:
                break

            modulo_violations = [v for v in violations if v[2] == 'modulo']
            for cluster_id, violation_amount, _ in modulo_violations:
                self._adjust_cluster_size_strong(X, labels, cluster_id, violation_amount, distances, delivery_freq)

        return labels

    def _check_all_violations(self, labels, delivery_freq):
        """全面检查所有约束违反情况"""
        violations = []

        for cluster_id in range(self.n_clusters):
            cluster_indices = np.where(labels == cluster_id)[0]

            if len(cluster_indices) == 0:
                violations.append((cluster_id, 13, 'empty'))
                continue

            cluster_freq = delivery_freq[cluster_indices]
            min_size = self._get_min_cluster_size(cluster_freq)

            current_size = len(cluster_indices)
            size_violation = min_size - current_size

            if size_violation > 0:
                violations.append((cluster_id, size_violation, 'under'))

        return violations

    def _add_points_to_cluster_strong(self, X, labels, target_cluster, n_points_needed, distances, delivery_freq):
        """强化版：添加点到满足最小规模约束"""
        n_samples = X.shape[0]

        other_cluster_points = np.where(labels != target_cluster)[0]
        if len(other_cluster_points) == 0:
            return

        target_distances = distances[other_cluster_points, target_cluster]
        nearest_indices = other_cluster_points[np.argsort(target_distances)]

        points_moved = 0
        for point_idx in nearest_indices:
            if points_moved >= n_points_needed:
                break

            original_cluster = labels[point_idx]
            original_cluster_indices = np.where(labels == original_cluster)[0]

            if len(original_cluster_indices) > 13:
                original_cluster_freq = delivery_freq[original_cluster_indices]
                original_min_size = self._get_min_cluster_size(original_cluster_freq)

                new_original_size = len(original_cluster_indices) - 1
                if new_original_size >= original_min_size:
                    labels[point_idx] = target_cluster
                    points_moved += 1

    def _adjust_cluster_size_strong(self, X, labels, cluster_id, remainder, distances, delivery_freq):
        """强化版：调整聚类大小"""
        cluster_indices = np.where(labels == cluster_id)[0]
        current_size = len(cluster_indices)

        cluster_freq = delivery_freq[cluster_indices]
        required_size = self._get_min_cluster_size(cluster_freq)

        if current_size > required_size:
            excess_points = current_size - required_size
            cluster_distances = distances[cluster_indices, cluster_id]
            farthest_indices = cluster_indices[np.argsort(-cluster_distances)[:excess_points]]

            for point_idx in farthest_indices:
                best_cluster = self._find_best_cluster_for_point(X, labels, point_idx, distances, delivery_freq)
                if best_cluster is not None:
                    labels[point_idx] = best_cluster

    def _find_best_cluster_for_point(self, X, labels, point_idx, distances, delivery_freq):
        """为点找到最适合的聚类"""
        current_cluster = labels[point_idx]
        best_cluster = None
        min_distance = float('inf')

        for cluster_id in range(self.n_clusters):
            if cluster_id == current_cluster:
                continue

            cluster_indices = np.where(labels == cluster_id)[0]
            if len(cluster_indices) > 0:
                cluster_freq = delivery_freq[cluster_indices]
                min_required = self._get_min_cluster_size(cluster_freq)

                new_size = len(cluster_indices) + 1
                if new_size >= min_required:
                    distance = distances[point_idx, cluster_id]
                    if distance < min_distance:
                        min_distance = distance
                        best_cluster = cluster_id

        return best_cluster

    def _local_search_optimization(self, X, labels, delivery_freq, max_iterations=100):
        """启发式局部搜索优化类内距离"""
        n_samples = X.shape[0]
        best_labels = labels.copy()
        best_total_distance = self._calculate_total_distance(X, best_labels)

        distances = cdist(X, X, metric='euclidean')

        for iteration in range(max_iterations):
            improved = False

            for point_idx in np.random.permutation(n_samples):
                current_cluster = labels[point_idx]
                original_labels = labels.copy()

                for target_cluster in range(self.n_clusters):
                    if target_cluster == current_cluster:
                        continue
                    labels[point_idx] = target_cluster
                    if self._check_constraints_satisfied(labels, delivery_freq):
                        new_total_distance = self._calculate_total_distance(X, labels)
                        if new_total_distance < best_total_distance:
                            best_labels = labels.copy()
                            best_total_distance = new_total_distance
                            improved = True
                            break
                    else:
                        labels[point_idx] = current_cluster

                labels[:] = original_labels
            if not improved:
                break
        return best_labels

    def _calculate_total_distance(self, X, labels):
        """计算所有聚类内的总距离"""
        total_distance = 0.0
        for cluster_id in range(self.n_clusters):
            cluster_indices = np.where(labels == cluster_id)[0]
            if len(cluster_indices) > 0:
                cluster_points = X[cluster_indices]
                cluster_center = np.mean(cluster_points, axis=0)
                distances = np.sqrt(np.sum((cluster_points - cluster_center) ** 2, axis=1))
                total_distance += np.sum(distances)
        return total_distance

    def _check_constraints_satisfied(self, labels, delivery_freq):
        """检查当前标签分配是否满足所有约束"""
        for cluster_id in range(self.n_clusters):
            cluster_indices = np.where(labels == cluster_id)[0]
            cluster_freq = delivery_freq[cluster_indices]
            min_size = self._get_min_cluster_size(cluster_freq)
            if len(cluster_indices) < min_size:
                return False
        return True

    def fit(self, warehouse_lng=None, warehouse_lat=None):
        """主拟合函数"""
        X = np.asarray((self.data[self.lng_col].values, self.data[self.lat_col].values)).T
        delivery_freq = self.data[self.freq_col].values
        self.delivery_freq = delivery_freq
        centers = self._init_centers(X)
        for iteration in range(self.max_iter):
            labels = self._assign_with_strong_constraints(X, centers, delivery_freq)

            new_centers = np.zeros_like(centers)
            for j in range(self.n_clusters):
                cluster_points = X[labels == j]
                if len(cluster_points) > 0:
                    new_centers[j] = cluster_points.mean(axis=0)
                else:
                    new_centers[j] = centers[j]
            center_shift = np.sqrt(np.sum((new_centers - centers) ** 2, axis=1))
            if np.max(center_shift) < self.tol:
                break
            centers = new_centers

        self.cluster_centers_ = centers
        self.labels_ = labels

        print("开始启发式搜索优化...")
        optimized_labels = self._local_search_optimization(X, labels, delivery_freq)
        self.labels_ = optimized_labels

        self.data = self.data.assign(cluster_id=self.labels_)
        self.cluster_center = self.getClusterCenter()
        self.data = pd.merge(self.data, self.cluster_center, on="cluster_id")

        if warehouse_lng is not None and warehouse_lat is not None:
            self.cdist_calc(warehouse_lng, warehouse_lat)

        return self
