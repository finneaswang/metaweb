<script lang="ts">
	import { onMount, getContext } from "svelte";
	import { user } from "$lib/stores";
	import { goto } from "$app/navigation";

	const i18n = getContext("i18n");

	let stats = {
		todayTasks: 0,
		pendingAssignments: 0,
		chatSessions: 0,
		weaknessCount: 0
	};

	let loading = true;

	onMount(async () => {
		if (!$user) {
			goto("/auth");
			return;
		}
		await loadDashboard();
	});

	const loadDashboard = async () => {
		try {
			loading = true;
			const token = localStorage.getItem("token");
			
			// 获取作业统计
			const assignmentsRes = await fetch("/api/v1/assignments/", {
				headers: { Authorization: `Bearer ${token}` }
			});
			
			if (assignmentsRes.ok) {
				const assignments = await assignmentsRes.json();
				stats.pendingAssignments = assignments.filter(a => a.status === "pending").length;
				stats.todayTasks = stats.pendingAssignments;
			}

			// 获取对话统计
			const chatsRes = await fetch("/api/v1/chats/", {
				headers: { Authorization: `Bearer ${token}` }
			});
			
			if (chatsRes.ok) {
				const chats = await chatsRes.json();
				stats.chatSessions = chats.length || 0;
			}

		} catch (error) {
			console.error("Failed to load dashboard:", error);
		} finally {
			loading = false;
		}
	};
</script>

<div class="p-8">
	<h2 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">
		欢迎回来，{$user?.name || "学生"} 👋
	</h2>
	<p class="text-gray-600 dark:text-gray-400 mb-8">
		今天是 {new Date().toLocaleDateString("zh-CN", {
			year: "numeric",
			month: "long",
			day: "numeric",
			weekday: "long"
		})}
	</p>

	{#if loading}
		<div class="flex items-center justify-center py-12">
			<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
		</div>
	{:else}
		<!-- 统计卡片 -->
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
			<div class="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
				<div class="flex items-center justify-between">
					<div>
						<p class="text-sm text-gray-600 dark:text-gray-400">今日待办</p>
						<p class="text-3xl font-bold text-gray-900 dark:text-white mt-2">
							{stats.todayTasks}
						</p>
					</div>
					<div class="text-4xl">📋</div>
				</div>
			</div>

			<div class="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
				<div class="flex items-center justify-between">
					<div>
						<p class="text-sm text-gray-600 dark:text-gray-400">待交作业</p>
						<p class="text-3xl font-bold text-gray-900 dark:text-white mt-2">
							{stats.pendingAssignments}
						</p>
					</div>
					<div class="text-4xl">📝</div>
				</div>
			</div>

			<div class="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
				<div class="flex items-center justify-between">
					<div>
						<p class="text-sm text-gray-600 dark:text-gray-400">对话次数</p>
						<p class="text-3xl font-bold text-gray-900 dark:text-white mt-2">
							{stats.chatSessions}
						</p>
					</div>
					<div class="text-4xl">💬</div>
				</div>
			</div>

			<div class="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
				<div class="flex items-center justify-between">
					<div>
						<p class="text-sm text-gray-600 dark:text-gray-400">需强化项</p>
						<p class="text-3xl font-bold text-gray-900 dark:text-white mt-2">
							{stats.weaknessCount}
						</p>
					</div>
					<div class="text-4xl">📊</div>
				</div>
			</div>
		</div>

		<!-- 快捷入口 -->
		<div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
			<a
				href="/dashboard/chat"
				class="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl p-6 text-white hover:shadow-lg transition transform hover:-translate-y-1"
			>
				<div class="text-4xl mb-3">💬</div>
				<h3 class="text-xl font-bold mb-2">开始对话</h3>
				<p class="text-blue-100">向AI提问，获取即时帮助</p>
			</a>

			<a
				href="/assignments"
				class="bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl p-6 text-white hover:shadow-lg transition transform hover:-translate-y-1"
			>
				<div class="text-4xl mb-3">📝</div>
				<h3 class="text-xl font-bold mb-2">查看作业</h3>
				<p class="text-purple-100">完成并提交你的作业</p>
			</a>

			<a
				href="/dashboard/evaluation"
				class="bg-gradient-to-br from-green-500 to-green-600 rounded-xl p-6 text-white hover:shadow-lg transition transform hover:-translate-y-1"
			>
				<div class="text-4xl mb-3">📊</div>
				<h3 class="text-xl font-bold mb-2">自我评估</h3>
				<p class="text-green-100">了解你的学习进度</p>
			</a>
		</div>

		<!-- 欢迎提示 -->
		<div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-6">
			<h3 class="text-lg font-semibold text-blue-900 dark:text-blue-100 mb-2">
				🎯 今日学习建议
			</h3>
			<p class="text-blue-700 dark:text-blue-300">
				欢迎使用学生秘书系统！你可以通过AI对话获取学习帮助，完成作业提交，并进行自我评估来追踪学习进度。
			</p>
		</div>
	{/if}
</div>
