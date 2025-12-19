<script lang="ts">
	import { onMount } from 'svelte';
	import { user } from '$lib/stores';
	import KnowledgeGraphViz from '$lib/components/KnowledgeGraphViz.svelte';

	let loading = true;
	let error = null;
	let selectedSubject = '';
	let subjects = [];
	let graphData = { nodes: [], edges: [] };
	let statistics = null;
	let selectedNode = null;
	let viewMode = 'graph'; // 'graph' or 'list'
	let graphViz; // Reference to the viz component
	let learningPath = null; // Ruta de aprendizaje recomendada
	let isLoadingPath = false; // Indicador de carga del path
	let showPathPanel = false; // Mostrar panel de ruta

	onMount(async () => {
		await Promise.all([fetchSubjects(), fetchStatistics()]);
		await fetchGraphData();
	});

	const fetchSubjects = async () => {
		try {
			const res = await fetch('/api/metaweb/knowledge-graph/subjects', {
				headers: {
					Authorization: `Bearer ${localStorage.token}`
				}
			});

			if (res.ok) {
				subjects = await res.json();
			}
		} catch (e) {
			console.error('Failed to fetch subjects:', e);
		}
	};

	const fetchStatistics = async () => {
		try {
			const res = await fetch('/api/metaweb/knowledge-graph/statistics', {
				headers: {
					Authorization: `Bearer ${localStorage.token}`
				}
			});

			if (res.ok) {
				statistics = await res.json();
			}
		} catch (e) {
			console.error('Failed to fetch statistics:', e);
		}
	};

	const fetchGraphData = async () => {
		loading = true;
		try {
			let url = '/api/metaweb/knowledge-graph';
			if (selectedSubject) {
				url += `?subject=${encodeURIComponent(selectedSubject)}`;
			}

			const res = await fetch(url, {
				headers: {
					Authorization: `Bearer ${localStorage.token}`
				}
			});

			if (res.ok) {
				graphData = await res.json();
			} else {
				error = '获取知识图谱失败';
			}
		} catch (e) {
			error = e.message;
		} finally {
			loading = false;
		}
	};

	const handleSubjectChange = () => {
		fetchGraphData();
	};

	const handleFitView = () => {
		if (graphViz) {
			graphViz.fitView();
		}
	};

	const handleResetLayout = () => {
		if (graphViz) {
			graphViz.resetLayout();
		}
	};

	const recommendLearningPath = async () => {
		if (!selectedSubject) {
			alert('请先选择一门科目');
			return;
		}

		isLoadingPath = true;
		showPathPanel = false;

		try {
			const res = await fetch(`/api/metaweb/knowledge-graph/learning-path/recommend?subject=${encodeURIComponent(selectedSubject)}`, {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${localStorage.token}`,
					'Content-Type': 'application/json'
				}
			});

			if (res.ok) {
				learningPath = await res.json();
				showPathPanel = true;

				// Highlight path in graph
				if (graphViz && learningPath.path) {
					graphViz.highlightPath(learningPath.path);
				}
			} else {
				alert('获取学习路径失败');
			}
		} catch (e) {
			console.error('Failed to get learning path:', e);
			alert('获取学习路径失败: ' + e.message);
		} finally {
			isLoadingPath = false;
		}
	};

	const clearLearningPath = () => {
		learningPath = null;
		showPathPanel = false;
		if (graphViz) {
			graphViz.clearHighlight();
		}
	};

	const getDifficultyColor = (level) => {
		if (level <= 2) return 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400';
		if (level <= 3) return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400';
		if (level <= 4) return 'bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-400';
		return 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400';
	};

	const getDifficultyLabel = (level) => {
		if (level <= 2) return '简单';
		if (level <= 3) return '中等';
		if (level <= 4) return '困难';
		return '很难';
	};

	const getMasteryColor = (level) => {
		if (level === null || level === undefined) return 'text-gray-500';
		if (level < 0.5) return 'text-yellow-600';
		if (level < 0.8) return 'text-blue-600';
		return 'text-green-600';
	};

	const getMasteryLabel = (level) => {
		if (level === null || level === undefined) return '未学习';
		if (level < 0.5) return '学习中';
		if (level < 0.8) return '基本掌握';
		return '完全掌握';
	};
</script>

<div class="min-h-screen p-6">
	<div class="max-w-7xl mx-auto">
		<!-- Header -->
		<div class="mb-6">
			<h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">知识图谱</h1>
			<p class="text-gray-600 dark:text-gray-400">交互式知识点体系可视化</p>
		</div>

		<!-- Statistics Cards -->
		{#if statistics}
			<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
				<div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
					<div class="text-sm text-gray-600 dark:text-gray-400 mb-1">总知识点数</div>
					<div class="text-3xl font-bold text-blue-600 dark:text-blue-400">
						{statistics.overall.total_knowledge_points}
					</div>
				</div>

				<div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
					<div class="text-sm text-gray-600 dark:text-gray-400 mb-1">覆盖科目数</div>
					<div class="text-3xl font-bold text-green-600 dark:text-green-400">
						{statistics.overall.total_subjects}
					</div>
				</div>

				<div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
					<div class="text-sm text-gray-600 dark:text-gray-400 mb-1">平均难度</div>
					<div class="text-3xl font-bold text-orange-600 dark:text-orange-400">
						{statistics.overall.average_difficulty.toFixed(1)}
					</div>
				</div>
			</div>
		{/if}

		<!-- Control Panel -->
		<div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm mb-6">
			<div class="flex flex-wrap items-center gap-4">
				<!-- Subject Filter -->
				<div class="flex-1 min-w-[200px]">
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						选择科目
					</label>
					<select
						bind:value={selectedSubject}
						on:change={handleSubjectChange}
						class="w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
					>
						<option value="">全部科目</option>
						{#each subjects as subject}
							<option value={subject}>{subject}</option>
						{/each}
					</select>
				</div>

				<!-- View Mode Toggle -->
				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						视图模式
					</label>
					<div class="flex gap-2">
						<button
							on:click={() => (viewMode = 'graph')}
							class="px-4 py-2 rounded-lg {viewMode === 'graph'
								? 'bg-blue-600 text-white'
								: 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'}"
						>
							图谱视图
						</button>
						<button
							on:click={() => (viewMode = 'list')}
							class="px-4 py-2 rounded-lg {viewMode === 'list'
								? 'bg-blue-600 text-white'
								: 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'}"
						>
							列表视图
						</button>
					</div>
				</div>

				<!-- Graph Controls -->
				{#if viewMode === 'graph'}
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							图谱控制
						</label>
						<div class="flex gap-2">
							<button
								on:click={handleFitView}
								class="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
							>
								适应视图
							</button>
							<button
								on:click={handleResetLayout}
								class="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
							>
								重置布局
							</button>
							<button
								on:click={recommendLearningPath}
								disabled={isLoadingPath || !selectedSubject}
								class="px-4 py-2 bg-pink-600 text-white rounded-lg hover:bg-pink-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
							>
								{isLoadingPath ? '生成中...' : '推荐学习路径'}
							</button>
							{#if showPathPanel}
								<button
									on:click={clearLearningPath}
									class="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
								>
									清除高亮
								</button>
							{/if}
						</div>
					</div>
				{/if}
			</div>
		</div>

		<!-- Main Content Area -->
		<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
			<!-- Graph/List View -->
			<div class="lg:col-span-2">
				{#if loading}
					<div class="flex items-center justify-center py-12 bg-white dark:bg-gray-800 rounded-lg">
						<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
					</div>
				{:else if error}
					<div class="bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 p-4 rounded-lg">
						{error}
					</div>
				{:else if viewMode === 'graph'}
					<!-- Interactive Graph View -->
					<div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
						<KnowledgeGraphViz
							bind:this={graphViz}
							{graphData}
							bind:selectedNode
						/>
					</div>

					<!-- Learning Path Panel -->
					{#if showPathPanel && learningPath}
						<div class="mt-6 bg-gradient-to-r from-pink-50 to-purple-50 dark:from-pink-900/10 dark:to-purple-900/10 rounded-lg p-6 shadow-lg border border-pink-200 dark:border-pink-800">
							<div class="flex items-center justify-between mb-4">
								<h3 class="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
									<svg class="w-6 h-6 text-pink-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
									</svg>
									推荐学习路径
								</h3>
								<button
									on:click={clearLearningPath}
									class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
								>
									<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
									</svg>
								</button>
							</div>

							<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
								<div class="bg-white dark:bg-gray-800 rounded-lg p-4">
									<div class="text-sm text-gray-600 dark:text-gray-400">总步骤</div>
									<div class="text-2xl font-bold text-pink-600 dark:text-pink-400">{learningPath.path.length}</div>
								</div>
								<div class="bg-white dark:bg-gray-800 rounded-lg p-4">
									<div class="text-sm text-gray-600 dark:text-gray-400">预计学时</div>
									<div class="text-2xl font-bold text-purple-600 dark:text-purple-400">{learningPath.estimated_hours}h</div>
								</div>
								<div class="bg-white dark:bg-gray-800 rounded-lg p-4">
									<div class="text-sm text-gray-600 dark:text-gray-400">平均难度</div>
									<div class="text-2xl font-bold text-blue-600 dark:text-blue-400">{learningPath.difficulty_avg.toFixed(1)}/5</div>
								</div>
							</div>

							<div class="bg-white dark:bg-gray-800 rounded-lg p-4">
								<h4 class="font-semibold text-gray-900 dark:text-white mb-3">学习顺序</h4>
								<div class="space-y-2 max-h-96 overflow-y-auto">
									{#each learningPath.details as step}
										<div class="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
											<div class="flex-shrink-0 w-8 h-8 bg-pink-600 text-white rounded-full flex items-center justify-center font-bold text-sm">
												{step.order}
											</div>
											<div class="flex-1">
												<div class="font-medium text-gray-900 dark:text-white">{step.name}</div>
												<div class="text-sm text-gray-600 dark:text-gray-400 flex items-center gap-2">
													<span>难度: {step.difficulty}/5</span>
													<span>•</span>
													<span>预计 {step.hours}h</span>
													{#if step.prerequisites.length > 0}
														<span>•</span>
														<span class="text-xs">前置: {step.prerequisites.join(', ')}</span>
													{/if}
												</div>
											</div>
										</div>
									{/each}
								</div>
							</div>
						</div>
					{/if}

					<!-- Legend -->
					<div class="mt-4 bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
						<h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">图例</h3>
						<div class="grid grid-cols-2 gap-4">
							<div>
								<div class="text-xs text-gray-600 dark:text-gray-400 mb-2">难度等级:</div>
								<div class="flex flex-wrap gap-2">
									<span class="px-2 py-1 rounded text-xs bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400">简单</span>
									<span class="px-2 py-1 rounded text-xs bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400">中等</span>
									<span class="px-2 py-1 rounded text-xs bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-400">困难</span>
									<span class="px-2 py-1 rounded text-xs bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400">很难</span>
								</div>
							</div>
							<div>
								<div class="text-xs text-gray-600 dark:text-gray-400 mb-2">关系类型:</div>
								<div class="flex flex-col gap-1 text-xs">
									<div class="flex items-center gap-2">
										<div class="w-8 h-0.5 bg-gray-700"></div>
										<span class="text-gray-700 dark:text-gray-300">前置关系</span>
									</div>
									<div class="flex items-center gap-2">
										<div class="w-8 h-0.5 bg-gray-400 border-dashed border-t-2"></div>
										<span class="text-gray-700 dark:text-gray-300">相关关系</span>
									</div>
								</div>
							</div>
						</div>
					</div>
				{:else}
					<!-- List View (original) -->
					<div class="grid grid-cols-1 gap-4">
						{#each graphData.nodes as node}
							<div
								class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
								on:click={() => (selectedNode = node)}
							>
								<div class="flex items-start justify-between mb-3">
									<div class="flex-1">
										<h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-1">
											{node.label}
										</h3>
										{#if node.category}
											<span
												class="inline-block px-2 py-1 text-xs rounded-full bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300"
											>
												{node.category}
											</span>
										{/if}
									</div>

									<span
										class="px-3 py-1 rounded-full text-sm font-medium {getDifficultyColor(
											node.difficulty_level
										)}"
									>
										{getDifficultyLabel(node.difficulty_level)}
									</span>
								</div>

								{#if node.mastery_level !== undefined}
									<div class="mb-3">
										<div class="flex items-center justify-between text-sm mb-1">
											<span class="text-gray-600 dark:text-gray-400">我的掌握度:</span>
											<span class={getMasteryColor(node.mastery_level)}>
												{getMasteryLabel(node.mastery_level)} ({(node.mastery_level * 100).toFixed(0)}%)
											</span>
										</div>
										<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
											<div
												class="h-2 rounded-full {getMasteryColor(node.mastery_level).replace('text-', 'bg-')}"
												style="width: {node.mastery_level * 100}%"
											></div>
										</div>
									</div>
								{/if}
							</div>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Node Detail Panel -->
			<div class="lg:col-span-1">
				{#if selectedNode}
					<div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm sticky top-6">
						<h3 class="text-2xl font-bold text-gray-900 dark:text-white mb-4">
							{selectedNode.label}
						</h3>

						<div class="space-y-4">
							<div>
								<div class="text-sm text-gray-600 dark:text-gray-400 mb-1">科目</div>
								<div class="text-gray-900 dark:text-white">{selectedNode.subject}</div>
							</div>

							{#if selectedNode.category}
								<div>
									<div class="text-sm text-gray-600 dark:text-gray-400 mb-1">分类</div>
									<div class="text-gray-900 dark:text-white">{selectedNode.category}</div>
								</div>
							{/if}

							<div>
								<div class="text-sm text-gray-600 dark:text-gray-400 mb-1">难度等级</div>
								<span
									class="px-3 py-1 rounded-full text-sm font-medium {getDifficultyColor(
										selectedNode.difficulty_level
									)}"
								>
									{getDifficultyLabel(selectedNode.difficulty_level)}
								</span>
							</div>

							{#if selectedNode.mastery_level !== undefined}
								<div>
									<div class="text-sm text-gray-600 dark:text-gray-400 mb-1">我的掌握度</div>
									<div class="flex items-center gap-2">
										<span class={getMasteryColor(selectedNode.mastery_level) + ' font-semibold'}>
											{(selectedNode.mastery_level * 100).toFixed(0)}%
										</span>
										<span class="text-sm {getMasteryColor(selectedNode.mastery_level)}">
											({getMasteryLabel(selectedNode.mastery_level)})
										</span>
									</div>
									<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mt-2">
										<div
											class="h-2 rounded-full {getMasteryColor(selectedNode.mastery_level).replace('text-', 'bg-')}"
											style="width: {selectedNode.mastery_level * 100}%"
										></div>
									</div>
								</div>
							{/if}

							<!-- Show prerequisites and related points from graph edges -->
							{#if graphData.edges}
								{@const prerequisites = graphData.edges
									.filter(e => e.to_node === selectedNode.label && e.relation_type === 'prerequisite')
									.map(e => e.from_node)}
								{@const relatedPoints = graphData.edges
									.filter(e =>
										(e.from_node === selectedNode.label || e.to_node === selectedNode.label) &&
										e.relation_type === 'related'
									)
									.map(e => e.from_node === selectedNode.label ? e.to_node : e.from_node)}

								{#if prerequisites.length > 0}
									<div>
										<div class="text-sm text-gray-600 dark:text-gray-400 mb-2">前置知识点</div>
										<div class="flex flex-wrap gap-1">
											{#each prerequisites as prereq}
												<span
													class="px-2 py-1 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 rounded text-xs"
												>
													{prereq}
												</span>
											{/each}
										</div>
									</div>
								{/if}

								{#if relatedPoints.length > 0}
									<div>
										<div class="text-sm text-gray-600 dark:text-gray-400 mb-2">相关知识点</div>
										<div class="flex flex-wrap gap-1">
											{#each relatedPoints as related}
												<span
													class="px-2 py-1 bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-400 rounded text-xs"
												>
													{related}
												</span>
											{/each}
										</div>
									</div>
								{/if}
							{/if}
						</div>
					</div>
				{:else}
					<div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-12 text-center">
						<div class="text-gray-500 dark:text-gray-400">
							{#if viewMode === 'graph'}
								点击图谱中的节点查看详情
							{:else}
								点击列表中的知识点查看详情
							{/if}
						</div>
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>