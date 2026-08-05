"""
REPORT SYSTEM MODULE - WhatsApp Ban Bot
Core reporting engine with API, Web, and Proxy layers
Base and credit by: LORD ZISKY
"""

import asyncio
import aiohttp
import random
import time
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import json

class ReportSystem:
    def __init__(self, db, proxy_harvester, fallback_system):
        self.db = db
        self.proxy_harvester = proxy_harvester
        self.fallbacks = fallback_system
        self.active_sessions = {}
        self.report_queue = asyncio.Queue()
        
        # Rate limiting
        self.rate_limits = {
            'api': {'count': 0, 'window_start': time.time()},
            'web': {'count': 0, 'window_start': time.time()},
            'proxy': {'count': 0, 'window_start': time.time()}
        }
    
    async def send_api_report(self, target_number: str, reporter_number: str, 
                            proxy: str = None) -> Dict:
        """Send report via WhatsApp API endpoints"""
        session_id = self.fallbacks.generate_fake_session_data()['session_id']
        template = self.fallbacks.get_report_template()
        
        payload = {
            'phone': target_number,
            'reporter': reporter_number or 'anonymous',
            'reason': template['reason'],
            'description': template['description'],
            'session_id': session_id,
            'timestamp': int(time.time()),
            'user_agent': self.fallbacks.get_random_user_agent(),
            'platform': 'web'
        }
        
        endpoints = [
            'https://web.whatsapp.com/api/report',
            'https://faq.whatsapp.com/api/v1/reports',
            'https://graph.facebook.com/whatsapp/report'
        ]
        
        headers = self.fallbacks.generate_headers(
            referer='https://web.whatsapp.com/'
        )
        
        async with aiohttp.ClientSession() as session:
            for endpoint in endpoints:
                try:
                    # Prepare proxy if available
                    proxy_url = f"http://{proxy}" if proxy else None
                    
                    async with session.post(
                        endpoint,
                        json=payload,
                        headers=headers,
                        proxy=proxy_url,
                        timeout=10,
                        ssl=False
                    ) as response:
                        
                        status = response.status
                        result = {
                            'method': 'api',
                            'endpoint': endpoint,
                            'status': status,
                            'success': 200 <= status < 300,
                            'proxy_used': proxy,
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        # Update proxy stats
                        self.db.update_proxy_stats(proxy, result['success'], f"HTTP {status}")
                        
                        return result
                        
                except Exception as e:
                    logging.error(f"API report failed {endpoint}: {e}")
                    continue
        
        return {'success': False, 'error': 'All API endpoints failed'}
    
    async def send_web_form_report(self, target_number: str, reporter_number: str,
                                 proxy: str = None) -> Dict:
        """Submit report through web forms"""
        template = self.fallbacks.get_report_template()
        
        form_data = {
            'phoneNumber': target_number,
            'reporterNumber': reporter_number or '',
            'issueType': template['reason'],
            'description': template['description'],
            'additionalDetails': template['details'],
            'countryCode': target_number[:3] if target_number.startswith('+') else '1',
            'language': 'en',
            'platform': 'ANDROID',
            'appVersion': '2.23.16.78',
            'deviceModel': 'Pixel 6',
            'osVersion': '13'
        }
        
        form_endpoints = [
            'https://www.whatsapp.com/contact/',
            'https://support.whatsapp.com/report/',
            'https://help.whatsapp.com/abuse'
        ]
        
        for endpoint in form_endpoints:
            try:
                headers = self.fallbacks.generate_headers()
                headers.update({
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Origin': 'https://www.whatsapp.com',
                    'X-Requested-With': 'XMLHttpRequest'
                })
                
                proxy_url = f"http://{proxy}" if proxy else None
                
                async with aiohttp.ClientSession() as session:
                    # First get CSRF token
                    async with session.get(
                        endpoint,
                        headers=headers,
                        proxy=proxy_url,
                        timeout=10
                    ) as get_resp:
                        html = await get_resp.text()
                        # Simple CSRF extraction (simplified)
                        csrf_token = 'abc123'  # In real implementation, parse from HTML
                    
                    form_data['csrf'] = csrf_token
                    
                    # Submit form
                    async with session.post(
                        endpoint,
                        data=form_data,
                        headers=headers,
                        proxy=proxy_url,
                        timeout=15
                    ) as post_resp:
                        
                        result = {
                            'method': 'web_form',
                            'endpoint': endpoint,
                            'status': post_resp.status,
                            'success': post_resp.status == 200 or 'thank' in (await post_resp.text()).lower(),
                            'proxy_used': proxy,
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        self.db.update_proxy_stats(proxy, result['success'], f"FORM {post_resp.status}")
                        return result
                        
            except Exception as e:
                logging.error(f"Web form failed {endpoint}: {e}")
                continue
        
        return {'success': False, 'error': 'All web forms failed'}
    
    async def send_proxy_report(self, target_number: str, reporter_number: str,
                              proxy_list: List[str]) -> List[Dict]:
        """Send reports through multiple proxies"""
        results = []
        
        # Limit concurrent proxies
        semaphore = asyncio.Semaphore(10)
        
        async def single_proxy_report(proxy: str) -> Dict:
            async with semaphore:
                # Randomly choose method
                method = random.choice(['api', 'web_form'])
                
                if method == 'api':
                    result = await self.send_api_report(target_number, reporter_number, proxy)
                else:
                    result = await self.send_web_form_report(target_number, reporter_number, proxy)
                
                result['proxy'] = proxy
                return result
        
        # Create tasks for all proxies
        tasks = [single_proxy_report(proxy) for proxy in proxy_list[:50]]  # Limit to 50
        
        # Run concurrently
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for res in batch_results:
            if isinstance(res, dict):
                results.append(res)
                # Log successful reports
                if res.get('success'):
                    self.db.add_reported_user(
                        target_number=target_number,
                        reporter_number=reporter_number,
                        report_type=res['method'],
                        report_method='proxy',
                        proxy_used=res.get('proxy'),
                        success=True
                    )
        
        return results
    
    async def execute_multi_layer_attack(self, target_number: str, 
                                       reporter_number: str = None) -> Dict:
        """Execute full ban_perm attack with all layers"""
        attack_id = f"ATTACK_{int(time.time())}_{hash(target_number)[:8]}"
        
        logging.info(f"Starting multi-layer attack {attack_id} on {target_number}")
        
        # Get available proxies
        proxy_stats = self.db.get_proxy_stats(limit=100)
        proxies = [p['proxy_address'] for p in proxy_stats if p['is_active']]
        
        if not proxies:
            proxies = self.fallbacks.get_emergency_proxies()
        
        results = {
            'attack_id': attack_id,
            'target': target_number,
            'reporter': reporter_number,
            'start_time': datetime.now().isoformat(),
            'layers': {},
            'summary': {}
        }
        
        # LAYER 1: API Reports
        results['layers']['api_reports'] = []
        for i in range(10):  # 10 API reports
            proxy = random.choice(proxies) if proxies else None
            result = await self.send_api_report(target_number, reporter_number, proxy)
            results['layers']['api_reports'].append(result)
            await asyncio.sleep(random.uniform(1, 3))
        
        # LAYER 2: Web Form Reports
        results['layers']['web_reports'] = []
        for i in range(5):  # 5 web form reports
            proxy = random.choice(proxies) if proxies else None
            result = await self.send_web_form_report(target_number, reporter_number, proxy)
            results['layers']['web_reports'].append(result)
            await asyncio.sleep(random.uniform(2, 4))
        
        # LAYER 3: Proxy Network Reports
        results['layers']['proxy_reports'] = await self.send_proxy_report(
            target_number, reporter_number, proxies[:20]
        )
        
        # Generate summary
        total_reports = (
            len(results['layers']['api_reports']) +
            len(results['layers']['web_reports']) +
            len(results['layers']['proxy_reports'])
        )
        
        successful_reports = sum(
            1 for layer in results['layers'].values()
            for report in (layer if isinstance(layer, list) else [])
            if isinstance(report, dict) and report.get('success')
        )
        
        results['summary'] = {
            'total_reports': total_reports,
            'successful_reports': successful_reports,
            'success_rate': (successful_reports / total_reports * 100) if total_reports > 0 else 0,
            'proxies_used': len(proxies[:20]),
            'duration_seconds': time.time() - time.mktime(
                datetime.strptime(results['start_time'], '%Y-%m-%dT%H:%M:%S.%f').timetuple()
            ),
            'end_time': datetime.now().isoformat()
        }
        
        # Update database statistics
        self.db.update_bot_stats(
            total_reports=total_reports,
            successful_bans=successful_reports
        )
        
        return results
    
    def check_rate_limit(self, report_type: str) -> bool:
        """Check if rate limit is exceeded"""
        now = time.time()
        limit_window = 60  # 60 seconds window
        
        if now - self.rate_limits[report_type]['window_start'] > limit_window:
            # Reset window
            self.rate_limits[report_type] = {'count': 0, 'window_start': now}
            return True
        
        max_limits = {
            'api': 20,    # 20 API reports per minute
            'web': 10,    # 10 web forms per minute
            'proxy': 50   # 50 proxy reports per minute
        }
        
        if self.rate_limits[report_type]['count'] < max_limits[report_type]:
            self.rate_limits[report_type]['count'] += 1
            return True
        
        return False
    
    async def queue_report(self, target_number: str, reporter_number: str,
                         report_type: str = 'auto') -> str:
        """Queue a report for processing"""
        report_id = f"REPORT_{int(time.time())}_{random.randint(1000, 9999)}"
        
        report_data = {
            'id': report_id,
            'target': target_number,
            'reporter': reporter_number,
            'type': report_type,
            'queued_at': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        await self.report_queue.put(report_data)
        
        # Start processor if not running
        if report_id not in self.active_sessions:
            self.active_sessions[report_id] = asyncio.create_task(
                self.process_report_queue()
            )
        
        return report_id
    
    async def process_report_queue(self):
        """Process queued reports"""
        while not self.report_queue.empty():
            try:
                report_data = await self.report_queue.get()
                
                logging.info(f"Processing report {report_data['id']}")
                
                if report_data['type'] == 'ban_perm':
                    result = await self.execute_multi_layer_attack(
                        report_data['target'],
                        report_data['reporter']
                    )
                elif report_data['type'] == 'proxy_only':
                    proxies = [p['proxy_address'] for p in self.db.get_proxy_stats(limit=20)]
                    result = await self.send_proxy_report(
                        report_data['target'],
                        report_data['reporter'],
                        proxies
                    )
                else:
                    # Auto-detect best method
                    result = await self.send_api_report(
                        report_data['target'],
                        report_data['reporter']
                    )
                
                # Update report status
                report_data['status'] = 'completed'
                report_data['result'] = result
                report_data['completed_at'] = datetime.now().isoformat()
                
                logging.info(f"Report {report_data['id']} completed")
                
            except Exception as e:
                logging.error(f"Queue processing error: {e}")
    
    def get_report_status(self, report_id: str) -> Optional[Dict]:
        """Get status of a specific report"""
        # Check active sessions
        for report in list(self.report_queue._queue):
            if isinstance(report, dict) and report.get('id') == report_id:
                return report
        
        return None
    
    def generate_report_summary(self, target_number: str = None,
                              hours: int = 24) -> Dict:
        """Generate report summary for dashboard"""
        # Get recent reports from database
        reported_users = self.db.get_reported_users(target_number)
        
        if not reported_users:
            return {'total': 0, 'success_rate': 0}
        
        # Filter by time
        cutoff = datetime.now().timestamp() - (hours * 3600)
        recent_reports = [
            r for r in reported_users
            if datetime.strptime(r['timestamp'], '%Y-%m-%d %H:%M:%S').timestamp() > cutoff
        ]
        
        successful = sum(1 for r in recent_reports if r['success'])
        total = len(recent_reports)
        
        return {
            'total_reports': total,
            'successful_reports': successful,
            'success_rate': (successful / total * 100) if total > 0 else 0,
            'timeframe_hours': hours,
            'unique_targets': len(set(r['target_number'] for r in recent_reports)),
            'report_methods': {
                'api': sum(1 for r in recent_reports if 'api' in r['report_method'].lower()),
                'web': sum(1 for r in recent_reports if 'web' in r['report_method'].lower()),
                'proxy': sum(1 for r in recent_reports if 'proxy' in r['report_method'].lower())
            }
        }

# Base and credit by: LORD ZISKY