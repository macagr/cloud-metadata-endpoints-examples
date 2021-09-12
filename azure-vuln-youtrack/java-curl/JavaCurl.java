import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.IOException;

public class JavaCurl {

	public static String getMetadataCredentialsKeyVault () {
		ProcessBuilder pb = new ProcessBuilder();
		pb.command("curl", "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https%3A%2F%2Fvault.azure.net", "-H", "Metadata:true");
		StringBuilder out = new StringBuilder();
		try {
			Process p = pb.start();

			BufferedReader reader = new BufferedReader(new InputStreamReader(p.getInputStream()));

			String line;

			while ((line = reader.readLine()) != null){
				out.append(line);
				out.append("\n");
			}

			int exitCode = p.waitFor();
			System.out.println("\nExited with error code: "+ exitCode);
		} catch (IOException e){
			e.printStackTrace();
		} catch (InterruptedException e) {
			e.printStackTrace();
		}
		return out.toString();
	}	

	public static String getMetadataCredentialsARM () {
		ProcessBuilder pb = new ProcessBuilder();
		pb.command("curl", "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https%3A%2F%2Fmanagement.azure.com", "-H", "Metadata:true");
		StringBuilder out = new StringBuilder();
		try {
			Process p = pb.start();

			BufferedReader reader = new BufferedReader(new InputStreamReader(p.getInputStream()));

			String line;

			while ((line = reader.readLine()) != null){
				out.append(line);
				out.append("\n");
			}

			int exitCode = p.waitFor();
			System.out.println("\nExited with error code: "+ exitCode);
		} catch (IOException e){
			e.printStackTrace();
		} catch (InterruptedException e) {
			e.printStackTrace();
		}
		return out.toString();
	}	

	// public static void main(String[] args) throws Exception
	// {
	//  	System.out.println(getMetadataCredentials());
	// } 
}