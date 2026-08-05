"""
⚡ PROXY MANAGER v2.0
Proxy harvesting, rotation, and management system
Base and credit by: LORD ZISKY
"""

import os
import re
import json
import time
import random
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import requests
from colorama import Fore, Style, init
import aiohttp
import sqlite3
from urllib.parse import urlparse

init(autoreset=True)

class ProxyHarvester:
    """Advanced proxy management with rotation and statistics"""
    
    def __init__(self, config):
        self.config = config
        self.all_proxies = []
        self.working_proxies = []
        self.failed_proxies = []
        self.proxy_stats = {}
        self.current_proxy_index = 0
        self.proxy_lock = threading.Lock()
        self.last_refresh = None
        
        # Proxy categories
        self.proxy_categories = {
            'http': [],
            'https': [],
            'socks4': [],
            'socks5': [],
            'premium': [],
            'anonymous': [],
            'elite': []
        }
        
        # Statistics
        self.stats = {
            'total_harvested': 0,
            'total_tested': 0,
            'working_count': 0,
            'failed_count': 0,
            'success_rate': 0.0,
            'requests_made': 0,
            'requests_failed': 0,
            'rotation_count': 0,
            'last_rotation': None
        }
        
        # Load existing proxies
        self.load_proxies()
        
        # Start maintenance thread
        self.maintenance_thread = threading.Thread(target=self._maintenance_loop, daemon=True)
        self.maintenance_thread.start()
        
        print(f"{Fore.GREEN}[PROXY] Proxy Manager initialized. Working proxies: {len(self.working_proxies)}")
    
    def _maintenance_loop(self):
        """Background maintenance thread"""
        while True:
            try:
                # Check proxy health every 30 minutes
                time.sleep(1800)
                self._health_check()
                
                # Auto-refresh if low on proxies
                if len(self.working_proxies) < self.config.MIN_WORKING_PROXIES:
                    print(f"{Fore.YELLOW}[PROXY] Low on proxies ({len(self.working_proxies)}). Auto-refreshing...")
                    self.harvest_proxies()
                    self.test_all_proxies()
                
            except Exception as e:
                print(f"{Fore.RED}[PROXY] Maintenance error: {e}")
    
    def _health_check(self):
        """Health check for working proxies"""
        if not self.working_proxies:
            return
        
        print(f"{Fore.CYAN}[PROXY] Running health check on {len(self.working_proxies)} proxies...")
        
        dead_proxies = []
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(self.test_proxy, proxy): proxy for proxy in self.working_proxies[:50]}
            
            for future in futures:
                proxy = futures[future]
                try:
                    if not future.result(timeout=10):
                        dead_proxies.append(proxy)
                except:
                    dead_proxies.append(proxy)
        
        # Remove dead proxies
        for proxy in dead_proxies:
            if proxy in self.working_proxies:
                self.working_proxies.remove(proxy)
                self.failed_proxies.append(proxy)
        
        if dead_proxies:
            print(f"{Fore.YELLOW}[PROXY] Removed {len(dead_proxies)} dead proxies")
            self.save_proxies()
    
    async def harvest_proxies_async(self) -> List[str]:
        """Asynchronous proxy harvesting"""
        print(f"{Fore.CYAN}[PROXY] Starting async proxy harvest from {len(self.config.PROXY_SOURCES)} sources...")
        
        all_proxies = []
        async with aiohttp.ClientSession() as session:
            tasks = []
            for source in self.config.PROXY_SOURCES:
                task = self._scrape_source_async(session, source)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_proxies.extend(result)
        
        # Remove duplicates
        unique_proxies = list(set(all_proxies))
        self.all_proxies = unique_proxies
        self.stats['total_harvested'] = len(unique_proxies)
        
        print(f"{Fore.GREEN}[PROXY] Harvested {len(unique_proxies)} unique proxies")
        return unique_proxies
    
    async def _scrape_source_async(self, session, url: str) -> List[str]:
        """Scrape proxies from a single source asynchronously"""
        try:
            async with session.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'}) as response:
                text = await response.text()
                
                # Multiple regex patterns for different proxy formats
                patterns = [
                    r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?):\d+\b',
                    r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{2,5}\b',
                    r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}:\d+\b',
                ]
                
                proxies = []
                for pattern in patterns:
                    found = re.findall(pattern, text)
                    proxies.extend(found)
                
                # Also look for JSON formatted proxies
                if 'json' in url or 'api' in url:
                    try:
                        data = await response.json()
                        if isinstance(data, list):
                            proxies.extend([p for p in data if ':' in str(p)])
                        elif 'proxies' in data:
                            proxies.extend(data['proxies'])
                    except:
                        pass
                
                return list(set(proxies))
                
        except Exception as e:
            print(f"{Fore.RED}[PROXY] Failed to scrape {url}: {e}")
            return []
    
    def harvest_proxies(self) -> List[str]:
        """Synchronous proxy harvesting"""
        print(f"{Fore.CYAN}[PROXY] Harvesting proxies from {len(self.config.PROXY_SOURCES)} sources...")
        
        all_proxies = []
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for source in self.config.PROXY_SOURCES:
                future = executor.submit(self._scrape_source_sync, source)
                futures.append(future)
            
            for future in futures:
                try:
                    proxies = future.result(timeout=30)
                    all_proxies.extend(proxies)
                except Exception as e:
                    print(f"{Fore.RED}[PROXY] Source failed: {e}")
        
        # Remove duplicates and validate
        unique_proxies = []
        seen = set()
        for proxy in all_proxies:
            if ':' in proxy and proxy not in seen:
                parts = proxy.split(':')
                if len(parts) == 2 and parts[1].isdigit() and 1 <= int(parts[1]) <= 65535:
                    unique_proxies.append(proxy)
                    seen.add(proxy)
        
        self.all_proxies = unique_proxies
        self.stats['total_harvested'] = len(unique_proxies)
        self.last_refresh = datetime.now()
        
        print(f"{Fore.GREEN}[PROXY] Harvested {len(unique_proxies)} valid proxies")
        return unique_proxies
    
    def _scrape_source_sync(self, url: str) -> List[str]:
        """Synchronous source scraping"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=15)
            
            patterns = [
                r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?):\d+\b',
                r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{2,5}\b',
            ]
            
            proxies = []
            for pattern in patterns:
                found = re.findall(pattern, response.text)
                proxies.extend(found)
            
            # Try JSON parsing for API endpoints
            if 'api' in url or 'json' in url:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        for item in data:
                            if ':' in str(item):
                                proxies.append(str(item))
                    elif isinstance(data, dict):
                        if 'proxies' in data:
                            proxies.extend(data['proxies'])
                        # Try to extract from nested structures
                        for value in data.values():
                            if isinstance(value, list):
                                for item in value:
                                    if ':' in str(item):
                                        proxies.append(str(item))
                except:
                    pass
            
            return list(set(proxies))
            
        except Exception as e:
            print(f"{Fore.RED}[PROXY] Failed {url}: {e}")
            return []
    
    def test_proxy(self, proxy: str) -> bool:
        """Test if a proxy is working"""
        try:
            proxies = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
            
            # Test with multiple URLs
            for test_url in self.config.PROXY_TEST_URLS:
                try:
                    response = requests.get(
                        test_url, 
                        proxies=proxies, 
                        timeout=8,
                        headers={'User-Agent': 'Mozilla/5.0'}
                    )
                    
                    if response.status_code == 200:
                        # Verify response contains valid data
                        if test_url == "http://httpbin.org/ip":
                            data = response.json()
                            if 'origin' in data:
                                # Check if origin matches proxy IP
                                proxy_ip = proxy.split(':')[0]
                                if proxy_ip in data['origin']:
                                    return True
                        else:
                            return True
                except:
                    continue
            
            return False
            
        except Exception:
            return False
    
    def test_all_proxies(self, max_workers: int = 50) -> Tuple[List[str], List[str]]:
        """Test all harvested proxies"""
        if not self.all_proxies:
            print(f"{Fore.RED}[PROXY] No proxies to test")
            return [], []
        
        print(f"{Fore.CYAN}[PROXY] Testing {len(self.all_proxies)} proxies with {max_workers} workers...")
        
        self.working_proxies = []
        self.failed_proxies = []
        
        tested = 0
        total = len(self.all_proxies)
        
        def test_and_track(proxy):
            nonlocal tested
            if self.test_proxy(proxy):
                self.working_proxies.append(proxy)
            else:
                self.failed_proxies.append(proxy)
            
            tested += 1
            if tested % 20 == 0:
                progress = (tested / total) * 100
                working = len(self.working_proxies)
                print(f"{Fore.CYAN}[PROXY] Progress: {tested}/{total} ({progress:.1f}%) - {working} working")
        
        # Test concurrently
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            list(executor.map(test_and_track, self.all_proxies))
        
        # Update statistics
        self.stats['total_tested'] = total
        self.stats['working_count'] = len(self.working_proxies)
        self.stats['failed_count'] = len(self.failed_proxies)
        self.stats['success_rate'] = (len(self.working_proxies) / total * 100) if total > 0 else 0
        
        print(f"{Fore.GREEN}[PROXY] Testing complete!")
        print(f"{Fore.GREEN}[PROXY] Working: {len(self.working_proxies)} | Failed: {len(self.failed_proxies)}")
        
        # Categorize proxies
        self._categorize_proxies()
        
        # Save results
        self.save_proxies()
        
        return self.working_proxies, self.failed_proxies
    
    def _categorize_proxies(self):
        """Categorize proxies by type and quality"""
        for proxy in self.working_proxies:
            # Simple categorization (in real implementation, use more sophisticated detection)
            if ':8080' in proxy or ':3128' in proxy:
                self.proxy_categories['http'].append(proxy)
            elif ':1080' in proxy or ':9050' in proxy:
                self.proxy_categories['socks5'].append(proxy)
            else:
                self.proxy_categories['https'].append(proxy)
    
    def get_next_proxy(self) -> Optional[str]:
        """Get next proxy in rotation"""
        with self.proxy_lock:
            if not self.working_proxies:
                print(f"{Fore.RED}[PROXY] No working proxies available")
                return None
            
            proxy = self.working_proxies[self.current_proxy_index]
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.working_proxies)
            self.stats['rotation_count'] += 1
            self.stats['last_rotation'] = datetime.now()
            
            return proxy
    
    def get_random_proxy(self) -> Optional[str]:
        """Get random working proxy"""
        if not self.working_proxies:
            return None
        
        return random.choice(self.working_proxies)
    
    def get_proxy_by_category(self, category: str) -> Optional[str]:
        """Get proxy from specific category"""
        if category in self.proxy_categories and self.proxy_categories[category]:
            return random.choice(self.proxy_categories[category])
        
        return self.get_random_proxy()
    
    def mark_proxy_failed(self, proxy: str):
        """Mark a proxy as failed"""
        with self.proxy_lock:
            if proxy in self.working_proxies:
                self.working_proxies.remove(proxy)
                self.failed_proxies.append(proxy)
                
                # Update current index if needed
                if self.current_proxy_index >= len(self.working_proxies):
                    self.current_proxy_index = 0
                
                print(f"{Fore.YELLOW}[PROXY] Marked proxy as failed: {proxy}")
    
    def save_proxies(self, filename: str = "data/proxies.json"):
        """Save proxies to file"""
        try:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            data = {
                'working_proxies': self.working_proxies,
                'failed_proxies': self.failed_proxies,
                'all_proxies': self.all_proxies,
                'stats': self.stats,
                'categories': self.proxy_categories,
                'last_update': datetime.now().isoformat(),
            }
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"{Fore.GREEN}[PROXY] Saved {len(self.working_proxies)} proxies to {filename}")
            
        except Exception as e:
            print(f"{Fore.RED}[PROXY] Failed to save proxies: {e}")
    
    def load_proxies(self, filename: str = "data/proxies.json"):
        """Load proxies from file"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    data = json.load(f)
                
                self.working_proxies = data.get('working_proxies', [])
                self.failed_proxies = data.get('failed_proxies', [])
                self.all_proxies = data.get('all_proxies', [])
                self.stats = data.get('stats', self.stats)
                self.proxy_categories = data.get('categories', self.proxy_categories)
                
                print(f"{Fore.GREEN}[PROXY] Loaded {len(self.working_proxies)} working proxies")
            else:
                print(f"{Fore.YELLOW}[PROXY] No proxy file found, starting fresh")
                
        except Exception as e:
            print(f"{Fore.RED}[PROXY] Failed to load proxies: {e}")
    
    def get_stats(self) -> Dict:
        """Get proxy statistics"""
        stats = self.stats.copy()
        stats.update({
            'current_working': len(self.working_proxies),
            'current_failed': len(self.failed_proxies),
            'categories_count': {k: len(v) for k, v in self.proxy_categories.items()},
            'last_refresh': self.last_refresh.isoformat() if self.last_refresh else None,
        })
        return stats
    
    def print_dashboard(self):
        """Print proxy dashboard"""
        print(f"\n{Fore.CYAN}╔════════════════════════════════════════════════╗")
        print(f"{Fore.CYAN}║              PROXY MANAGER DASHBOARD           ║")
        print(f"{Fore.CYAN}╚════════════════════════════════════════════════╝")
        
        print(f"{Fore.GREEN}📊 Working Proxies: {len(self.working_proxies)}")
        print(f"{Fore.RED}📊 Failed Proxies: {len(self.failed_proxies)}")
        print(f"{Fore.YELLOW}📊 Success Rate: {self.stats.get('success_rate', 0):.1f}%")
        print(f"{Fore.CYAN}🔄 Rotations: {self.stats.get('rotation_count', 0)}")
        print(f"{Fore.MAGENTA}📡 Requests Made: {self.stats.get('requests_made', 0)}")
        
        print(f"\n{Fore.YELLOW}📂 Proxy Categories:")
        for category, proxies in self.proxy_categories.items():
            if proxies:
                print(f"  {Fore.WHITE}• {category}: {len(proxies)} proxies")
        
        if self.working_proxies:
            print(f"\n{Fore.GREEN}🔧 Sample Working Proxies:")
            for proxy in self.working_proxies[:3]:
                print(f"  {Fore.WHITE}→ {proxy}")
