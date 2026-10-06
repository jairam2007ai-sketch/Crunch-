<script setup>
import { onMounted } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import ToastStack from '../shared/components/ToastStack.vue'
import { inr } from '../shared/format'
import { loadMenu, useMenu } from '../shared/menu'
import CartSheet from './components/CartSheet.vue'
import { cart, cartCount, cartTotal } from './cart'

const { menu } = useMenu()
onMounted(() => loadMenu().catch(() => {}))
</script>

<template>
  <header class="sticky top-0 z-40 border-b-[3px] border-turmeric bg-char text-[#FFF7DA] shadow-[0_10px_20px_-12px_rgba(0,0,0,.6)]">
    <div class="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-2">
      <RouterLink to="/" class="mini-lock" aria-label="Customize Your Crunch, home"><span class="a">Customize Your</span><span class="b">CRUNCH</span></RouterLink>
      <div class="flex items-center gap-3">
        <span v-if="menu.data" class="hidden items-center gap-2 text-sm font-semibold sm:inline-flex">
          <span class="h-2.5 w-2.5 rounded-full" :class="menu.data.shop.is_open ? 'bg-[#5BC27E]' : 'bg-[#F06C5E]'" />
          {{ menu.data.shop.is_open ? 'Taking orders' : 'Not taking online orders' }}
        </span>
        <button class="btn btn-yellow btn-sm" type="button" @click="cart.open = true">
          Your order
          <span class="rounded-full bg-char px-2 text-xs text-turmeric tabular-nums">{{ cartCount }}</span>
          <span v-if="cartCount" class="tabular-nums">{{ inr(cartTotal) }}</span>
        </button>
      </div>
    </div>
  </header>
  <RouterView />
  <footer class="border-t-[3px] border-turmeric bg-char text-[#FFF7DA]">
    <div class="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-6">
      <p class="m-0 flex flex-wrap items-center gap-x-3 font-hand text-xl font-bold text-turmeric">
        <span>Small steps</span><span class="text-[#FFF7DA]">→</span><span>Real customers</span><span class="text-[#FFF7DA]">→</span><span>Big dreams</span>
      </p>
      <p class="m-0 text-sm opacity-80">Customize Your Crunch · Fresh · Tasty · Affordable · 100% veg</p>
    </div>
  </footer>
  <CartSheet />
  <ToastStack />
</template>
