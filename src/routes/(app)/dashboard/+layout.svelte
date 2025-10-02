<script lang="ts">
	import { page } from "$app/stores";
	import { user } from "$lib/stores";
	import { goto } from "$app/navigation";
	import { onMount, getContext } from "svelte";

	const i18n = getContext("i18n");

	onMount(() => {
		if (!$user) {
			goto("/auth");
		}
	});

	const navItems = [
		{ icon: "🏠", label: "首页", path: "/dashboard" },
		{ icon: "💬", label: "AI对话", path: "/dashboard/chat" },
		{ icon: "📝", label: "作业中心", path: "/assignments" },
		{ icon: "📊", label: "自我评估", path: "/dashboard/evaluation" },
		{ icon: "👤", label: "学习画像", path: "/dashboard/profile" }
	];
</script>

<div class="flex h-screen bg-gray-50 dark:bg-gray-900">
	<!-- 侧边栏 -->
	<aside class="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col">
		<div class="p-6">
			<h1 class="text-2xl font-bold text-gray-900 dark:text-white">
				学生秘书
			</h1>
			<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
				欢迎回来，{$user?.name || "学生"}
			</p>
		</div>

		<nav class="mt-6 px-3 flex-1">
			{#each navItems as item}
				<a
					href={item.path}
					class="flex items-center gap-3 px-4 py-3 mb-2 rounded-lg transition
								 {$page.url.pathname === item.path
						? "bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
						: "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"}"
				>
					<span class="text-xl">{item.icon}</span>
					<span class="font-medium">{item.label}</span>
				</a>
			{/each}
		</nav>

		<!-- 底部用户信息 -->
		<div class="p-4 border-t border-gray-200 dark:border-gray-700">
			<div class="flex items-center gap-3">
				<div class="w-10 h-10 rounded-full bg-blue-500 flex items-center justify-center text-white font-bold">
					{$user?.name?.charAt(0).toUpperCase() || "S"}
				</div>
				<div class="flex-1 min-w-0">
					<p class="text-sm font-medium text-gray-900 dark:text-white truncate">
						{$user?.name || "学生"}
					</p>
					<p class="text-xs text-gray-500 dark:text-gray-400 truncate">
						{$user?.email || ""}
					</p>
				</div>
			</div>
		</div>
	</aside>

	<!-- 主内容区 -->
	<main class="flex-1 overflow-auto">
		<slot />
	</main>
</div>
