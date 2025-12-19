<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	let reports = [];
	let loading = true;
	let studentId = '';
	let filterType = 'all'; // all, weekly, monthly

	const fetchReports = async () => {
		loading = true;
		try {
			let url = `/api/metaweb/profiles/students/${studentId}/reports?`;
			if (filterType !== 'all') url += `report_type=${filterType}&`;
			url += 'limit=20';

			const res = await fetch(url, {
				headers: { Authorization: `Bearer ${localStorage.token}` }
			});

			if (!res.ok) throw new Error('Failed to fetch');
			reports = await res.json();
		} catch (error) {
			console.error('Error:', error);
			toast.error('加载失败');
		} finally {
			loading = false;
		}
	};

	onMount(async () => {
		if (!$user) {
			goto('/');
			return;
		}

		studentId = $user.role === 'student' ? $user.id : $user.id;
		await fetchReports();
	});

	$: if (filterType) {
		fetchReports();
	}

	const formatDate = (dateStr) => {
		if (!dateStr) return '';
		return new Date(dateStr).toLocaleDateString('zh-CN');
	};

	const parseJSON = (str) => {
		try {
			return JSON.parse(str);
		} catch {
			return [];
		}
	};

	const getReportTypeLabel = (type) => {
		const labels = {
			'daily': '每日总结',
			'weekly': '每周报告',
			'monthly': '每月分析'
		};
		return labels[type] || type;
	};

	const getReportIcon = (type) => {
		const icons = {
			'daily': '📅',
			'weekly': '📊',
			'monthly': '📈'
		};
		return icons[type] || '📄';
	};
</script>

<svelte:head>
	<title>学习报告 | Open WebUI</title>
</svelte:head>

<div class="flex flex-col h-full">
	<!-- Header -->
	<div class="p-6 border-b border-gray-100 dark:border-gray-800">
		<div class="flex items-center gap-2 mb-4">
			<button
				on:click={() => goto('/workspace/profile')}
				class="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
			>
				← 返回
			</button>
		</div>
		<h1 class="text-2xl font-semibold text-gray-900 dark:text-white">
			📈 学习报告
		</h1>

		<!-- Filter -->
		<div class="mt-4">
			<select
				bind:value={filterType}
				class="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
			>
				<option value="all">全部报告</option>
				<option value="daily">每日总结</option>
				<option value="weekly">每周报告</option>
				<option value="monthly">每月分析</option>
			</select>
		</div>
	</div>

	<!-- Content -->
	<div class="flex-1 overflow-y-auto p-6">
		{#if loading}
			<div class="flex justify-center items-center h-64">
				<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 dark:border-white"></div>
			</div>
		{:else if reports.length > 0}
			<div class="space-y-4">
				{#each reports as report}
					<div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
						<!-- Header -->
						<div class="flex justify-between items-start mb-4">
							<div class="flex items-center gap-3">
								<span class="text-2xl">{getReportIcon(report.report_type)}</span>
								<div>
									<div class="flex items-center gap-2">
										<h3 class="text-lg font-semibold text-gray-900 dark:text-white">
											{getReportTypeLabel(report.report_type)}
										</h3>
										{#if report.subject}
											<span class="text-sm px-2 py-1 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
												{report.subject}
											</span>
										{/if}
									</div>
									<div class="text-sm text-gray-600 dark:text-gray-400 mt-1">
										{formatDate(report.period_start)} - {formatDate(report.period_end)}
									</div>
								</div>
							</div>
							<div class="text-xs text-gray-500">
								生成于: {formatDate(report.generated_at)}
							</div>
						</div>

						<!-- Summary -->
						{#if report.summary}
							<div class="mb-4">
								<div class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
									📝 总结
								</div>
								<div class="text-gray-900 dark:text-white">
									{report.summary}
								</div>
							</div>
						{/if}

						<!-- Strengths & Weaknesses -->
						<div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
							<!-- Strengths -->
							{#if report.strengths}
								{@const strengths = parseJSON(report.strengths)}
								{#if strengths.length > 0}
									<div class="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
										<div class="text-sm font-medium text-green-700 dark:text-green-300 mb-2">
											✅ 强项
										</div>
										<ul class="space-y-1">
											{#each strengths as strength}
												<li class="text-sm text-green-800 dark:text-green-200">
													• {strength}
												</li>
											{/each}
										</ul>
									</div>
								{/if}
							{/if}

							<!-- Weaknesses -->
							{#if report.weaknesses}
								{@const weaknesses = parseJSON(report.weaknesses)}
								{#if weaknesses.length > 0}
									<div class="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-4">
										<div class="text-sm font-medium text-yellow-700 dark:text-yellow-300 mb-2">
											⚠️ 待提升
										</div>
										<ul class="space-y-1">
											{#each weaknesses as weakness}
												<li class="text-sm text-yellow-800 dark:text-yellow-200">
													• {weakness}
												</li>
											{/each}
										</ul>
									</div>
								{/if}
							{/if}
						</div>

						<!-- Recommendations -->
						{#if report.recommendations}
							<div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
								<div class="text-sm font-medium text-blue-700 dark:text-blue-300 mb-2">
									💡 建议
								</div>
								<div class="text-sm text-blue-800 dark:text-blue-200">
									{report.recommendations}
								</div>
							</div>
						{/if}

						<!-- Generator -->
						<div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 text-xs text-gray-500">
							由 {report.generated_by === 'ai' ? 'AI秘书' : '教师'} 生成
						</div>
					</div>
				{/each}
			</div>
		{:else}
			<div class="text-center text-gray-600 dark:text-gray-400 mt-8">
				<div class="text-4xl mb-2">📊</div>
				<div>暂无学习报告</div>
				<div class="text-sm mt-2">
					AI秘书将在每周日23:00自动生成周报
				</div>
			</div>
		{/if}
	</div>
</div>
