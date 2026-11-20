#include<bits/stdc++.h>
using namespace std;
#define int long long
#define ff first
#define ss second
#define all(v) (v).begin(), (v).end()
#define hha(x) cout << #x << ": " << x << " "
#define hhal(x) cout << #x << ": " << x << endl
#define print(v) cout << #v << ": "; for(auto x : v) cout << x << " "; cout << endl;

char a[105][105];
bool b[105][105];
void solve()
{
    int n;
    cin >> n;

    for(int i = 1; i <= n; i++) {
        for(int j = 1; j <= n; j++) {
            cin >> a[i][j];
        }
    }
    // char last;
    for(int i = 1; i <= n; i++) {
        char x = '#';
        int loc = -1;

        for(int j = 1; j <= n; j++) {
            if(a[i][j] != '.') {
                loc = j;
                x = a[i][j];
                break;
            }
        }

        for(int j = loc + 1; j <= n; j++) {
            if(!b[i][j] || a[i][j] != '.') break;
            a[i][j] = x;
        }
        for(int j = loc - 1; j > 0; j--) {
            if(!b[i][j] || a[i][j] != '.') break;
            a[i][j] = x;
        }

        for(int j = loc; j <= n; j++) {
            if(!b[i - 1][j] || a[i - 1][j] != '.') break;
            a[i - 1][j] = x;
        }
        for(int j = loc - 1; j > 0; j--) {
            if(!b[i - 1][j] || a[i - 1][j] != '.') break;
            a[i - 1][j] = x;
        }


        for(int j = 1; j <= n; j++) b[i][j] = 1;
        for(int j = 1; j <= n; j++) b[j][loc] = 1;

        // last = x;
    }

    for(int i = n; i > 0; i--) {
        for(int j = 1; j <= n; j++) {
            if(a[i][j] == '.') a[i][j] = a[i + 1][j];
        }
    }

    for(int i = 1; i <= n; i++) {
        for(int j = 1; j <= n; j++) {
            cout << a[i][j];
        }
        cout << "\n";
    }

}
signed main()
{
    ios::sync_with_stdio(0); cin.tie(NULL);
    // int t; cin >> t; while(t--)
    solve();
}
