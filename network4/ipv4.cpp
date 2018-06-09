#include "sysInclude.h"  
#include <vector>
#include <algorithm>

using std::vector;
 
extern void fwd_LocalRcv(char *pBuffer, int length);
extern void fwd_SendtoLower(char *pBuffer, int length, unsigned int nexthop);
extern void fwd_DiscardPkt(char *pBuffer, int type);
extern unsigned int getIpv4Address();

struct RNode
{
	int dest;
	int masklen;
	int nexthop;
	RNode(int d = 0, int m = 0, int n = 0) :
		dest(d), masklen(m), nexthop(n)
	{}
};

vector<RNode> routeTable;

void stud_Route_Init()
{
	routeTable.clear();
	return;
}

bool cmp(const RNode & a, const RNode & b)
{
	if (htonl(a.dest) > htonl(b.dest))
	{
		return true;
	}
	else if (htonl(a.dest) == htonl(b.dest))
	{
		return htonl(a.masklen) > htonl(b.masklen);
	}
	else
	{
		return false;
	}

}

void stud_route_add(stud_route_msg *proute)
{
	int dest;
	routeTable.push_back(RNode(ntohl(proute->dest), ntohl(proute->masklen), ntohl(proute->nexthop)));
	sort(routeTable.begin(), routeTable.end(), cmp);
	return;
}

int stud_fwd_deal(char *pBuffer, int length)
{
	int version = pBuffer[0] >> 4;
	int ihl = pBuffer[0] & 0xf;
	int ttl = (int)pBuffer[8];
	
	int dstIP = ntohl(*(unsigned int*)(pBuffer + 16));

	if (dstIP == getIpv4Address())            
	{                                                       
		fwd_LocalRcv(pBuffer, length);
		return 0;
	}

	if (ttl <= 0)                                  
	{
		fwd_DiscardPkt(pBuffer, STUD_FORWARD_TEST_TTLERROR);
		return 1;
	}

	for (vector<RNode>::iterator ii = routeTable.begin(); ii != routeTable.end(); ii++)     
	{
		if (ii->dest == dstIP)                     
		{
			char *buffer = new char[length];
			memcpy(buffer, pBuffer, length);
			buffer[8]--;                                    
			int sum = 0;                                    
			unsigned short int localCheckSum = 0;
			for (int i = 0; i < 2 * ihl; i++)
			{
				if (i == 5)
					continue;
				sum = sum + (buffer[i * 2] << 8) + (buffer[i * 2 + 1]);
				sum %= 65535;
			}
			localCheckSum = htons(0xffff - (unsigned short int)sum);
			memcpy(buffer + 10, &localCheckSum, sizeof(short unsigned int));
			fwd_SendtoLower(buffer, length, ii->nexthop);         
			return 0;
		}
	}
	fwd_DiscardPkt(pBuffer, STUD_FORWARD_TEST_NOROUTE);       
	return 1;
}
